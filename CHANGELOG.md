# CHANGELOG

すべての変更は Keep a Changelog の方針に準拠して記載しています。  
このプロジェクトの初回リリース（v0.1.0）で導入された主要な機能・設計方針・注意点を日本語でまとめています。

なお日付はパッケージ内のバージョン（src/kabusys/__init__.py）および本リリース作成日時に基づきます。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-31
初回公開リリース。

### Added
- パッケージ基盤
  - kabusys パッケージの初期構成を追加（src/kabusys/__init__.py）。
  - バージョン定義: 0.1.0。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env/.env.local の自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パーサー実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、コメント扱いのルール等。
  - 環境変数から取得する Settings クラスを追加（J-Quants トークン、kabu API、Slack、DBパス、監視しきい値、環境/ログレベル判定等）。
  - env 値・LOG_LEVEL の妥当性チェック（許容値の検証）を実装。

- AI モジュール（src/kabusys/ai）
  - ニュースNLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini, JSON mode）へバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込み。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）の計算（calc_news_window）。
    - バッチサイズ、記事数・文字数トリム、リトライ（指数バックオフ）等の制御。
    - レスポンスバリデーションとスコアクリップ（±1.0）。
    - 部分成功時に既存スコアを過度に消さないための idempotent な DELETE → INSERT ロジック。
    - フェイルセーフ設計: API失敗時はスキップして継続、例外は呼び出し元へ最小限伝播。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照し、ma200_ratio を計算、マクロ記事の抽出、OpenAI 呼び出し（gpt-4o-mini）でマクロセンチメント算出（最大記事数制限・リトライ実装）。
    - レジームスコアの合成と market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API やパース失敗時は macro_sentiment=0.0 として継続するフェイルセーフ。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能に設計。

- データプラットフォーム（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダーの夜間バッチ更新 job（calendar_update_job）と market_calendar を用いた営業日判定機能を実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DBデータがない場合の曜日ベースフォールバック（土日を非営業日）を実装。DBが部分的にしか存在しない場合でも一貫した判定を返す設計。
    - 最大探索日数、バックフィル、健全性チェック等を備えた堅牢な設計。
    - jquants_client 経由での取得・保存フローを想定（jq.fetch_market_calendar、jq.save_market_calendar の呼び出し）。
  - ETL パイプライン（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）
    - ETLResult データクラスを公開（etlモジュールで再エクスポート）。
    - 差分取得、idempotent 保存（save_*）、品質チェック（quality モジュール）を想定した ETL のインターフェースとユーティリティ関数を整備。
    - デフォルトのバックフィル日数、カレンダー先読み等のポリシーを定義。
    - DuckDB を前提としたテーブル存在チェック、最大日付取得ユーティリティ等を実装。
  - その他データユーティリティの骨組み（jquants_client, quality 等への参照を含む設計）。

- リサーチ（src/kabusys/research）
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Value（PER/ROE）、Volatility（20日 ATR）、Liquidity（20日平均売買代金・出来高比率）などのファクター計算を実装。
    - DuckDB の SQL ウィンドウ関数を多用し、データ不足時は None を返す安全設計。
    - 計算は prices_daily / raw_financials のみ参照し、本番発注 API 等にアクセスしない方針。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - Spearman（ランク相関）に基づく IC 計算、ties の扱いのため丸めによる安定化などの実装。
  - re-exports（src/kabusys/research/__init__.py）
    - 主要関数群をパッケージAPIとして公開。

- データ統計ユーティリティとの連携
  - zscore_normalize を kabusys.data.stats から再エクスポートするエントリ（research/__init__.py）を用意。

### Design / Notes
- ルックアヘッドバイアス対策
  - AI モジュール、リサーチ・ETL 等、すべてのモジュールで datetime.today() / date.today() を直接参照しない設計。target_date を呼び出し元から渡すことで意図しないルックアヘッドを防止。
  - DB クエリは target_date 未満 / 排他条件を適切に設定。

- リトライとフォールバック
  - OpenAI/API 呼び出しには429・ネットワークエラー・タイムアウト・5xx に対する指数バックオフリトライを実装。再試行消費時は安全側のデフォルト値（例: macro_sentiment=0.0）にフォールバック。
  - JSON レスポンスパースの堅牢化（前後の余計なテキストを取り除く処理）を実施。

- DB 書き込みの冪等性
  - ai_scores / market_regime / market_calendar など、更新は基本的に既存行の削除→挿入もしくは ON CONFLICT 相当の手法で冪等に行うよう設計。
  - DuckDB の executemany の特性（空リスト不可等）を考慮した実装。

- テスト容易性
  - OpenAI 呼び出し点はモジュール内のプライベート関数（_call_openai_api）を通しており、unittest.mock.patch による差し替えが容易。
  - 設定読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD によりテスト時の副作用を抑制可能。

### Known issues / TODO
- monitoring パッケージは __all__ に含まれているが、今回のコード一覧に監視関連の具体的実装ファイルが含まれていません。監視 (monitoring) 機能の実装 / 提供は今後の課題。
- jquants_client, quality 等の外部連携モジュールは参照ポイントのみ実装想定で、実装状況により追加作業が必要。
- DuckDB へのバインドやバージョン差異（list 型パラメータバインドの挙動など）に注意。コード内に互換性対策あり。

### Security
- 本リリースでは秘密情報（APIキー等）は環境変数経由での取り扱いを前提とし、コードにハードコードされていません。取り扱い方法は README/Deployment ドキュメントで明確化することを推奨。

---

この CHANGELOG はコードベースの実装から推測した変更点・設計意図に基づいて作成しています。実際のコミット履歴やリリースノートと差分がある場合は、差分に応じて更新してください。