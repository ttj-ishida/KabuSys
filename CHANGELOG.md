# Changelog

すべての重要な変更は Keep a Changelog の慣習に従って記録します。  
このファイルは主にコードベースから推測して記載しています（実装済みの機能・設計方針・エラー処理等を要約）。

※日付は本コード確認日（2026-04-02）を使用しています。

## [Unreleased]

## [0.1.0] - 2026-04-02

初回リリース。以下の主要機能・モジュールを実装・公開。

### Added
- パッケージ基盤
  - kabusys パッケージの公開インターフェース（data, strategy, execution, monitoring）。
  - バージョン情報: __version__ = "0.1.0"。

- 設定・環境変数管理（kabusys.config）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動的に読み込む仕組みを実装。
  - .env パーサーの堅牢化:
    - コメント行・空行を無視、export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理対応。
    - クォートなしの値におけるインラインコメント処理（直前が空白/タブの場合のみコメントと扱う）。
  - 自動ロード無効化フラグ(KABUSYS_DISABLE_AUTO_ENV_LOAD)をサポート。
  - Settings クラスを提供（J-Quants / kabuステーション / Slack / DBパス / 監視閾値 / 環境・ログレベル等のプロパティ）。
  - 必須環境変数未設定時は ValueError を送出する _require を実装。

- AI モジュール（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用い、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）の JSON Mode を使用して -1.0〜1.0 のセンチメントスコアを算出。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で計算。
    - バッチ処理（_BATCH_SIZE=20）、記事数/文字数のトリム制御（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - レスポンス検証ロジック（JSON復元、results 配列・code/score チェック、数値検証、スコアクリップ）。
    - エラー耐性: 429/ネットワーク断/タイムアウト/5xx に対する指数的バックオフと再試行。重大な失敗は個別チャンクをスキップして継続（フェイルセーフ）。
    - ai_scores へ冪等的に書き込む（対象コードのみ DELETE → INSERT）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）200日移動平均乖離（重み70%）とマクロセンチメント（重み30%）を合成して market_regime を日次判定。
    - マクロニュース抽出（マクロキーワード群）→ OpenAI による JSON 出力のセンチメント取得（_score_macro）。
    - API 呼び出しのリトライ/バックオフ、JSONパース失敗時は macro_sentiment=0.0 にフォールバック。
    - DuckDB を用いた ma200_ratio の計算と、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - 設計上ルックアヘッドバイアスを避ける（datetime.today() を直接参照せず、target_date 未満のデータのみ使用）。

- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルの存在チェック、営業日判定（is_trading_day）、前後営業日取得(next_trading_day/prev_trading_day)、期間内営業日列挙(get_trading_days)、SQ日判定(is_sq_day) を実装。
    - DB にカレンダーがない場合は曜日ベース（週末除外）でフォールバックする一貫したロジック。
    - calendar_update_job により J-Quants から差分取得して冪等的に保存（バックフィルと健全性チェック付き）。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult dataclass を公開（取得数・保存数・品質問題・エラー等を保持）。
    - 差分更新・バックフィル・品質チェックの設計方針を反映（データ範囲算出、idempotent 保存、品質問題は収集して呼び出し元で判断）。
    - jquants_client 経由で API を利用する設計（クライアント抽象化）。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- リサーチ・ファクター（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20日 ATR、相対ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB の SQL と Python ロジックで計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None ハンドリング、ログ出力。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部依存を使わず標準ライブラリでランク・統計を計算する実装。
  - research パッケージから主要関数を再エクスポート。

- その他
  - OpenAI API 呼び出しについて: news_nlp と regime_detector の双方で JSON Mode を使用し、モジュール間でプライベート呼び出し実装は共有しない方針（テスト差し替えや結合低減のため）。
  - ログ出力・警告の充実（各種フォールバックや失敗時に詳細ログを残す設計）。
  - 設定により DuckDB/SQLite/PID ファイルパスや監視しきい値（CPU/MEM/DISK）を指定可能に。

### Changed
- 初回リリースにつき該当なし（基本的に新規実装）。

### Fixed
- 初回リリースにつき該当なし（ただし各モジュールにフェイルセーフやエッジケース処理を多数実装）。

### Security
- 環境変数（OpenAI API キー、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN 等）が未設定の場合は明示的にエラーを出す設計（_require / ValueError）。  
  - 自動ロードは OS 環境変数優先で、.env の上書きは .env.local によって意図的に行える。OS 環境変数は保護される（protected set）。

### Notes / Implementation & 設計上の留意点
- ルックアヘッドバイアス回避のため、target_date ベースで過去データを参照し、datetime.today() 等を直接参照しない実装方針を一貫して採用しています（AI スコア生成・レジーム判定・リサーチ等）。
- DuckDB のバージョン互換性（executemany の空リスト不可、リストバインドの挙動）に配慮した実装が行われています。
- OpenAI 呼び出しはリトライ／バックオフ設計になっており、API の一時エラーがアプリ全体を停止させないフェイルセーフを採用しています。
- 一部モジュールは外部クライアント（jquants_client）や DB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime 等）に依存します。実行には前提となる DB スキーマ・外部 API 設定が必要です。

---

将来的な改良案（示唆）
- 大量 API 呼び出し時の並列化（現状はバッチ・逐次リトライ）
- テスト/モック用のインターフェース抽象化の強化（現状は unittest.mock.patch を想定）
- ai モデルの選択肢を設定で切替可能にする（現状は gpt-4o-mini に固定）
- 監視・運用ドキュメント（設定例 .env.example、DB スキーマ定義、ジョブスケジュール例）の追加

----- 
（この CHANGELOG はコードの実装内容から推測して作成しています。実際のリリースノートとして利用する場合は、必要に応じて担当者が修正・追記してください。）