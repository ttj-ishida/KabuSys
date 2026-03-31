CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します（Keep a Changelog 準拠）。
セマンティックバージョニングを採用しています。

なお、本 CHANGELOG は提供されたコードベースの内容から推測して作成しています。
実際のコミット履歴やリリース日付は環境に合わせて調整してください。

## [0.1.0] - 2026-03-31 (初期リリース)

### 追加 (Added)
- パッケージ初期公開:
  - kabusys パッケージの公開 (src/kabusys/__init__.py)。
  - パッケージバージョン: 0.1.0。

- 環境・設定管理:
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装（src/kabusys/config.py）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - OS 側の既存環境変数は保護され、.env の上書きを制御可能。
    - 自動読み込みを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い等に対応。
  - Settings クラスを提供:
    - J-Quants / kabuステーション / Slack / データベース関連等のプロパティ（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, DUCKDB_PATH 等）。
    - KABUSYS_ENV（development / paper_trading / live）・LOG_LEVEL のバリデーション。
    - is_live / is_paper / is_dev の便利プロパティ。

- AI 関連:
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）:
    - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）にバッチ送信してセンチメント（-1.0〜1.0）を取得、ai_scores テーブルへ書き込み。
    - 一度の API コールで最大 20 銘柄を処理するバッチ仕様（_BATCH_SIZE=20）。
    - 各銘柄は最新記事を最大 10 件・最大 3000 文字にトリムしてプロンプトに含める。
    - OpenAI の JSON Mode を利用し、厳密な JSON 応答を期待。応答パース失敗時でも外側の {} を抽出して復元を試みるフェールセーフ実装。
    - リトライ・バックオフ戦略（429・ネットワーク断・タイムアウト・5xx を対象、指数バックオフ）。
    - テスト用に _call_openai_api をパッチ可能。
    - DuckDB への書き込みは部分失敗に配慮して、スコア取得済みコードのみ DELETE → INSERT で置換（冪等性維持）。
    - DuckDB 0.10 の executemany 空リスト制約を考慮した実装。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - MA 計算は target_date 未満のデータのみ参照しルックアヘッドバイアスを排除。
    - マクロニュースは news_nlp の calc_news_window を使ってウィンドウ抽出、OpenAI（gpt-4o-mini）でセンチメントを取得。
    - API エラー時は macro_sentiment=0.0 として継続するフェイルセーフ設計。
    - market_regime テーブルへの冪等的書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - OpenAI 呼び出しは独立実装（news_nlp と内部関数を共有しない設計）。

- データプラットフォーム:
  - ETL パイプラインの公開インターフェース（src/kabusys/data/etl.py, pipeline.py）。
    - ETLResult データクラス（取得数・保存数・品質チェック結果・エラー集約等を保持）。
    - 差分取得、バックフィル、品質チェック（quality モジュールと連携）を想定した設計。
  - マーケットカレンダー管理モジュール（src/kabusys/data/calendar_management.py）:
    - market_calendar を用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - J-Quants API から差分でカレンダーを取得して冪等的に保存する calendar_update_job。
    - カレンダー未取得時は曜日ベース（平日）によるフォールバック。DB に部分的なデータしかない場合でも一貫した判定を行う。
    - バックフィル・先読み・健全性チェックの実装。

- リサーチモジュール:
  - ファクター計算（src/kabusys/research/factor_research.py）:
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER/ROE）を DuckDB 上で計算する関数を提供（calc_momentum, calc_volatility, calc_value）。
    - 返却は (date, code) をキーとする辞書リスト。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を提供。
    - pandas 等に依存しない標準ライブラリ実装。

- 共通・ユーティリティ:
  - DuckDB を主なデータストアに想定し、SQL と Python の組合せで処理を実装。
  - ロギングを各モジュールに埋め込み。多数の debug/info/warning メッセージを含む。
  - 設計上、datetime.today()/date.today() を直接参照しない箇所が明示され、ルックアヘッドバイアスを防ぐ方針を採用。

### 変更 (Changed)
- （初期リリースにおける設計注記として）OpenAI の応答ハンドリングとリトライ/バックオフ戦略を採用して堅牢性を重視。
- DuckDB のバージョン差異（executemany の空リスト取り扱い）に対応する実装方針を採用。
- .env パーシング挙動の詳細（コメント扱い、クォート処理、export 取り扱い）を明文化。

### 修正 (Fixed)
- OpenAI の JSON レスポンスが前後に余計なテキストを含む場合のパース復旧処理を実装（JSON の最外殻 {} を抽出して再パース）。
- API 5xx / ネットワークエラー等の扱いを明確化し、限度回数のリトライ後に安全にフォールバックする挙動を導入（例: macro_sentiment=0.0）。

### セキュリティ (Security)
- 機密情報（API キー等）は Settings 経由で環境変数から取得する設計。.env の自動読み込みを無効化する環境変数（KABUSYS_DISABLE_AUTO_ENV_LOAD）を提供し、テスト時や CI での秘密情報漏洩リスクを低減可能。

### 既知の制限・注意点 (Known issues / Notes)
- OpenAI クライアントとして openai.OpenAI を利用（モデル: gpt-4o-mini 固定設定）。API 仕様や SDK バージョンの変更により挙動が変わる可能性あり。
- DuckDB のバージョン依存性（特に executemany の挙動）に注意。コード内に互換性対策を含むが、実行環境の DuckDB バージョンでは追加調整が必要な場合がある。
- ai モジュールは外部 API（OpenAI）に依存するため、API 利用制限や課金に注意。
- news_nlp と regime_detector は設計上モジュール結合を避けるため内部 API 呼出しを分離している（テスト用にモック可能）。

---

その他: 今後のリリースでは以下を検討すると良い
- 単体テスト・統合テストの追加（OpenAI 呼出しのモックと DuckDB テーブルのフィクスチャ化）。
- OpenAI レスポンスのより詳細なスキーマ検証と異常時のアラート強化。
- J-Quants / kabu API クライアントの具象実装とリトライ/認証の改善。
- パフォーマンス改善（大量銘柄処理時のメモリ効率、DuckDB クエリ最適化）。