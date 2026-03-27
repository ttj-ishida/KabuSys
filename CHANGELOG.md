# Changelog

すべての注目すべき変更履歴を記載します。本ファイルは Keep a Changelog の形式に準拠しています。  

現在のパッケージバージョン: 0.1.0

## [Unreleased]
- （現時点の開発中の変更はここに記載します）

## [0.1.0] - 2026-03-27
初回リリース。日本株自動売買システムのコアライブラリを提供します。主な機能と設計上のポイントは以下の通りです。

### Added
- パッケージ基盤
  - パッケージ初期化と公開 API を提供（kabusys.__init__）。
  - バージョン情報 __version__ = "0.1.0" を設定。

- 環境変数 / 設定管理（kabusys.config）
  - .env / .env.local の自動読み込みを実装（プロジェクトルートの探索は .git / pyproject.toml を基準）。
  - 自動読み込み無効化用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサを実装（export 構文対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理など）。
  - 環境変数上書きの挙動（override / protected）を考慮した読み込みロジック。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境／ログレベル判定等のプロパティを公開。
  - KABUSYS_ENV, LOG_LEVEL の検証を実装。is_live / is_paper / is_dev の便宜プロパティ。

- データプラットフォーム（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）を実装。
    - 差分取得、バックフィル、品質チェック（quality モジュールとの連携）、Idempotent 保存をサポート。
    - ETLResult データクラスを提供し、実行結果・品質問題・エラーの集約を可能に。
  - ETL で使用する定数（初期ロード日、バックフィル日数、カレンダー参照範囲など）を設定。
  - カレンダー管理（kabusys.data.calendar_management）を実装。
    - market_calendar を用いた営業日判定、next/prev_trading_day、get_trading_days、is_sq_day、夜間更新ジョブ（calendar_update_job）を提供。
    - DB 未取得時の曜日ベースフォールバック、バックフィル再取得、健全性チェック（未来日付の異常判定）などを実装。
  - ETL インターフェース再エクスポート（kabusys.data.etl）で ETLResult を公開。

- 研究（research）モジュール（kabusys.research）
  - factor_research: ファクター計算（モメンタム、ボラティリティ／流動性、バリュー）を実装。
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）・相対 ATR（atr_pct）・20 日平均売買代金・出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（EPS が 0 または欠損時は None）。
  - feature_exploration: 将来リターン・IC（Information Coefficient）・ランク／統計サマリーを提供。
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: スピアマン（ランク）相関で IC を算出（有効レコードが3件未満の場合は None）。
    - rank / factor_summary: ランク化（同順位は平均ランク）・列別統計量を提供。
  - research パッケージの便利な再エクスポート（zscore_normalize 等）を整備。

- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）でセンチメントをスコア化して ai_scores テーブルへ書き込む処理を実装。
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して比較）。
    - チャンク処理（_BATCH_SIZE=20）と、1 銘柄あたりの記事数・文字数上限（過剰トークン対策）を実装。
    - JSON Mode を用いた API 呼び出しと厳密なレスポンスバリデーション（results キー・コード・スコアの型チェック）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。その他エラーはスキップして継続。
    - レスポンスパース時の耐性（前後の余計なテキストが混入した場合の {} 抽出）を実装。
    - API 呼び出し箇所はテスト用に patch 可能（_call_openai_api を差し替え可）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動 ETF）の 200 日 MA 乖離（重み70%）とマクロセンチメント（重み30%）を合成して market_regime テーブルに日次で書き込む機能を実装。
    - マクロニュースは news_nlp のウィンドウ計算を利用してタイトルを抽出、OpenAI（gpt-4o-mini）により JSON 出力で macro_sentiment を得る。
    - API の再試行ロジック、API 失敗時のフォールバック（macro_sentiment = 0.0）、スコアのクリッピング、閾値に基づくラベリング（bull/neutral/bear）を実装。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で行い、失敗時は ROLLBACK を試行して例外を上位に伝播。

### Changed
- （初回リリースのため該当なし）

### Fixed / Robustness
- API 耐障害性とフェイルセーフ
  - OpenAI API 呼び出しでの各種例外（RateLimitError, APIConnectionError, APITimeoutError, 5xx 等）に対するリトライとログ出力を実装し、最終的にフェイルした場合は安全側のデフォルト値（例: macro_sentiment=0.0）で継続する設計にした。
  - JSON パースやレスポンスフォーマット不整合時は WARN ログを出して該当チャンクをスキップし、他のデータ処理を継続。
- データ不足時の明示的フォールバック
  - MA200 計算に必要なデータが不足する場合は中立値（ma200_ratio=1.0 / ma200_dev を None）を採用し、警告ログを出力。
  - ai_scores / market_regime への書き込みは書き換え対象コードを限定して部分失敗時に既存データを保護。
- データベーストランザクションの安全性
  - ETL / AI 書き込み処理は BEGIN / COMMIT / ROLLBACK を明示的に使用。ROLLBACK 失敗時は警告ログを出力。

### Security
- API キーの扱い
  - OpenAI API キーは引数で注入可能（テストでのモック容易化）。未指定時は環境変数 OPENAI_API_KEY を参照し、未設定なら ValueError を送出して明示的に失敗する設計。

### Other notes / 設計方針（主要な注意点）
- ルックアヘッドバイアス対策
  - 日時の解決に datetime.today()/date.today() を直接参照しない（target_date に依存する設計）。DB クエリも target_date 未満／以前の条件を用いて将来データを参照しないよう配慮。
- テスト容易性
  - OpenAI 呼び出しポイントや内部関数を差し替え可能にしてユニットテストを書きやすくしている。
- 外部依存
  - DuckDB を主要なローカル格納／クエリ基盤として使用。OpenAI クライアント（openai.OpenAI）を用いた外部 API 呼び出しを行うため、稼働時には対応する API キーとネットワークが必要。
- 未実装 / 今後の拡張候補
  - research.calc_value での PBR / 配当利回りは未実装（注釈あり）。
  - quality モジュールの具体的チェックルールや jquants_client の実装、外部との統合テストは別途整備が必要。

---

著者注: 本 CHANGELOG は提供されたコードベースの実装内容・ドキュメントストリングから推測して作成しています。外部モジュール（jquants_client, quality など）の実装詳細や実運用上の挙動は、その実装に依存します。必要であれば、各モジュール（特に外部 API 呼び出し周り）の細かい変更点や将来のリリース計画を詳述します。