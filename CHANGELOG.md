# Changelog

すべての注目すべき変更点をこのファイルで管理します。  
フォーマットは "Keep a Changelog" に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-28

### Added
- パッケージ初期リリース (kabusys 0.1.0)
  - パッケージバージョンを src/kabusys/__init__.py に定義。
  - パッケージ外部公開モジュール: data, strategy, execution, monitoring を __all__ に設定。

- 環境設定・読み込み機能 (src/kabusys/config.py)
  - .env/.env.local ファイルと OS 環境変数から設定を自動ロード（プロジェクトルートを .git / pyproject.toml から検出）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。
  - .env パーサ実装:
    - export プレフィックス対応、シングル/ダブルクォート処理、バックスラッシュエスケープ、行内コメント処理。
    - 無効行やキー無し行の無視。
  - 上書き制御: override / protected による上書き保護（OS 環境変数を保護）。
  - 自動ロード無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスで主要設定をプロパティ化:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - データベースパス (DUCKDB_PATH, SQLITE_PATH)
    - 環境モード (KABUSYS_ENV) とログレベル (LOG_LEVEL) のバリデーション
    - is_live / is_paper / is_dev のユーティリティプロパティ
  - 必須環境変数未設定時は ValueError を発生させる _require 関数。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を集約し、OpenAI (gpt-4o-mini) を用いて銘柄ごとのセンチメントを算出して ai_scores に書き込み。
    - ウィンドウ計算 (前日 15:00 JST ～ 当日 08:30 JST) を calc_news_window で提供。
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄あたりの最大記事数・文字数制限、トリムを実装。
    - JSON mode を前提とした応答パースと堅牢なバリデーション (_validate_and_extract)。
    - リトライ（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実施。失敗時はフォールバックし処理継続（フェイルセーフ）。
    - スコアを ±1.0 にクリップ。
    - DuckDB への書き込みは冪等性を保つため DELETE → INSERT の方式で実装。部分失敗時に既存データを保護する設計。
    - テスト容易性: _call_openai_api をパッチで差し替え可能。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200日移動平均乖離 (重み 70%) とニュース由来のマクロセンチメント (重み 30%) を合成して daily market_regime を算出。
    - マクロ記事フィルタリング用キーワード群を定義。
    - OpenAI 呼び出しは JSON mode で行い、再試行・5xx 判定・レスポンスパース失敗時は macro_sentiment=0.0 で継続。
    - レジームラベル（bull / neutral / bear）判定ロジックと、DuckDB への冪等書き込み実装 (BEGIN/DELETE/INSERT/COMMIT)。
    - ルックアヘッドバイアス対策として datetime.today() を参照せず、prices_daily のクエリに date < target_date の排他条件を使用。

- データプラットフォーム関連 (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar を使った営業日判定・次営業日/前営業日取得・期間内営業日取得・SQ判定を提供。
    - DB 登録がない場合は曜日ベースのフォールバック（週末を非営業日）で一貫して動作。
    - カレンダー更新ジョブ (calendar_update_job) を実装（J-Quants から差分取得、バックフィル、健全性チェック）。
    - 最大探索日数上限やバックフィル日数などの安全策を実装。
  - ETL パイプライン (src/kabusys/data/pipeline.py / etl.py)
    - ETL 実行結果を表す dataclass ETLResult を公開。
    - 差分取得、保存（jquants_client を利用した冪等保存）、品質チェック（quality モジュール）を想定した設計。
    - テーブル存在チェック、最大日付取得などのユーティリティを実装。
    - バックフィル・カレンダー先読みなどの運用パラメータを備える。

- リサーチモジュール (src/kabusys/research)
  - factor_research.py
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Volatility（20日 ATR、相対ATR、出来高比率、平均売買代金）、Value（PER、ROE）などのファクター算出関数を実装。
    - DuckDB 上の SQL とウィンドウ関数を活用した実装。データ不足時は None を返す設計。
  - feature_exploration.py
    - 将来リターン計算 (calc_forward_returns)、IC（calc_ic）、ランク変換 (rank)、ファクター要約統計 (factor_summary) を実装。
    - rank 関数は ties の扱いで平均ランクを返し、丸め (round 12) による ties 検出改善を行う。
  - パッケージ再エクスポート: 主要関数を kabusys.research からアクセス可能に。

### Changed
- (初回リリースのため該当なし)

### Fixed
- (初回リリースのため該当なし)

### Security
- OpenAI API キーを引数で注入可能にし、環境変数 OPENAI_API_KEY が未設定の場合は ValueError を送出して明示的にエラー化。
- .env 読み込み時に OS 環境変数を保護する protected セットを導入し、意図せぬ上書きを防止。

### Notes / 設計上の重要点
- ルックアヘッドバイアス防止:
  - AI 系の処理（news_nlp, regime_detector）は datetime.today()/date.today() を参照せず、caller が渡す target_date を基準に窓を計算する設計。
- フェイルセーフ:
  - 外部 API 呼び出し（OpenAI, J-Quants）での失敗時は、可能な限り処理を継続して安全側のデフォルト値（例: macro_sentiment=0.0）を使用。
- 冪等性:
  - DuckDB への書き込みは既存行を削除してから挿入するなど、再実行耐性を考慮した実装。
- DuckDB 互換性:
  - executemany に空リストを渡せない等の実装制約（DuckDB 0.10）を考慮した防御的コーディング。
- テスト性:
  - OpenAI 呼び出し箇所は関数を分離しており、unittest.mock.patch による差し替えが容易。

---

（本 CHANGELOG はコードベースから機能・設計を推測して作成しています。実際のリリースノート用途には実装者による追記・確認を推奨します。）