# Changelog

すべての重要な変更点はこのファイルに記録します。本書式は「Keep a Changelog」準拠で、セマンティックバージョニングに従います。

- 変更ログのフォーマット: https://keepachangelog.com/ja/1.0.0/
- バージョニング: https://semver.org/lang/ja/

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買プラットフォームの基礎モジュール群を追加しました。主にデータ取得/ETL、研究（リサーチ）機能、AI を用いたニュース解析と市場レジーム判定、環境設定管理などを実装しています。

### Added
- パッケージ基盤
  - kabusys パッケージ初期実装（src/kabusys/__init__.py）。
  - 公開モジュール一覧に data, strategy, execution, monitoring を想定したエクスポートを定義。

- 環境設定 / .env 管理（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env 行パーサーを実装（コメント行、export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
  - 読み込み時の保護機能（OS 環境変数の上書き保護）を実装。
  - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス等の環境変数取得とバリデーションを行う（必須キー未設定時は ValueError）。
  - KABUSYS_ENV / LOG_LEVEL の許容値チェック、利便性プロパティ（is_live / is_paper / is_dev）を追加。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約し、銘柄ごとに記事を結合して OpenAI（gpt-4o-mini）の JSON Mode でバッチ解析。
    - タイムウィンドウ計算（JST 前日15:00〜当日08:30 相当の UTC 範囲）を calc_news_window() で提供。
    - バッチサイズ、記事数上限、文字数トリム、スコアクリッピング（±1.0）等の制限を実装。
    - API 呼び出しで 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフのリトライ実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列検査、コード整合性、数値チェック）と部分書き換えによる冪等保存（DELETE → INSERT）。
    - テスト容易性のため OpenAI 呼び出し箇所をパッチ差し替え可能に設計。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）を判定。
    - マクロセンチメントはマクロキーワードでフィルタしたニュースタイトルを LLM（gpt-4o-mini）に投げ JSON 応答で受け取り評価。
    - API エラーやパース失敗時にはフェイルセーフで macro_sentiment = 0.0 を採用。
    - スコア合成後、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実行。

- Data モジュール（src/kabusys/data）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録あり→DB 値優先、未登録日は曜日ベースでフォールバックする一貫した設計。
    - JPX カレンダーの夜間差分更新ジョブ calendar_update_job を実装（J-Quants クライアント経由で取得 → 保存）。
    - 安全性・健全性チェック（最大探索日数、バックフィル、未来日付の異常検出）を実装。

  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - 差分取得・保存・品質チェックのフレームワーク（ETLResult データクラスを公開）。
    - 最終取得日からの差分取得、backfill による後出し修正取り込み、品質チェックの集約を想定。
    - DuckDB を利用したテーブル存在チェック、最大日付取得などのユーティリティ実装。

- Research / ファクター計算（src/kabusys/research）
  - calc_momentum, calc_volatility, calc_value（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（20 日 ATR、相対 ATR、流動性指標）、Value（PER, ROE）を計算。
    - DuckDB のウィンドウ関数を活用し、営業日ベースのラグ/移動平均を算出。
    - データ不足時は None を返す等の堅牢な取り扱い。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）に対する fwd_Xd を算出。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を実装（最小有効レコード数チェック）。
    - ランク変換（rank）: 同順位は平均ランク、丸めによる ties 対策を実装。
    - ファクター統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- OpenAI API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を参照する実装。API キー未設定時は ValueError を発生させることで誤動作を防止。

### Notes / 設計上の重要点
- ルックアヘッドバイアス対策: 各 AI / 研究処理で datetime.today() / date.today() を直接参照しない設計。全て target_date を明示的に受け取り、DB クエリも target_date 未満／等で排他条件を取るなどの配慮あり。
- フェイルセーフ: LLM 呼び出しや外部 API 失敗時は例外を直ちに上位へ伝播させず、既定の中立値（例: macro_sentiment=0.0）やスキップ動作を取り入れてシステム全体の堅牢性を確保。
- 冪等性: DB への書き込みは既存行の削除 → 挿入、または ON CONFLICT を想定した実装で部分失敗時の被害を最小化。
- テスト容易性: OpenAI 呼び出し箇所（_call_openai_api 等）をモジュール内で分離し、unittest.mock.patch により差し替え可能に設計。

---

将来のバージョンでは、strategy / execution / monitoring の具体実装（発注経路、ポートフォリオ運用、運用監視アラート）や J-Quants / kabu クライアントの実実装、CI テスト、ドキュメントの拡充を予定しています。もし CHANGELOG に追加してほしい修正・補足があれば教えてください。