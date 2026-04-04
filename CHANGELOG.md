# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
このファイルは、提供されたコードベースから推測される機能追加・設計方針・既知の挙動を基に作成しています。

なお、[] 内の比較リンク（例: [Unreleased]）はプロジェクトのリポジトリ URL に合わせて適宜設定してください。

## [Unreleased]

- なし（現時点では新規未リリースの変更はありません）

## [0.1.0] - 2026-04-04

初回リリース。日本株自動売買プラットフォーム「KabuSys」のコア機能群を実装。

### 追加 (Added)

- 基本パッケージ
  - パッケージ情報とエクスポートを定義 (kabusys.__init__; __version__ = 0.1.0)。
  - 公開サブモジュール: data, strategy, execution, monitoring を想定。

- 設定管理 (kabusys.config)
  - 環境変数/.env 管理機能を実装。
    - プロジェクトルート検出: .git または pyproject.toml を基準に自動検出（CWD 非依存）。
    - .env/.env.local 自動ロード（優先順位: OS 環境変数 > .env.local > .env）。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数に対応（テスト用途）。
    - .env 行パーサ: export プレフィックス、クォート（シングル/ダブル）内のエスケープ、インラインコメントの扱い等に対応。
    - override/protected による上書き制御（OS 環境変数を保護）。
  - Settings クラスを提供。主要プロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、OPENAI関連のトークン、データベースパス、監視閾値、環境判定など）を環境変数から取得し、未設定時に ValueError を送出する必須設定取得ヘルパを実装。
  - 有効な環境値チェック（KABUSYS_ENV, LOG_LEVEL）。

- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols データを集約して LLM（gpt-4o-mini）へバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST の記事を対象。UTC に変換して DB 比較）。
    - 1 銘柄あたり最大記事数・最大文字数でトリム (_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK)。
    - 1 API 呼び出しで最大 20 銘柄を処理するチャンクング（_BATCH_SIZE）。
    - JSON Mode を前提としたレスポンスバリデーション（results 配列・code/score 検査、スコアの数値化・有限値チェック、±1.0 にクリップ）。
    - リトライ・バックオフ処理（429、ネットワークエラー、タイムアウト、5xx に対する指数バックオフ）。失敗時は該当チャンクをスキップして他チャンクを継続。
    - DuckDB の executemany に関する互換性対策（空リストは送らない等）。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
    - スコア取得後は ai_scores を日付＋コードで差し替え（DELETE → INSERT）し、部分失敗時に既存スコア破壊を避ける。

  - レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日毎に market_regime テーブルへ保存。
    - prices_daily から ma200_ratio を計算（target_date 未満のデータのみ使用、ルックアヘッド防止）。
    - raw_news からマクロキーワードで記事タイトルを抽出し、OpenAI により macro_sentiment を取得。
    - 合成スコアのクリップと閾値判定で regime_label を決定（bull/neutral/bear）。
    - DB へは冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）、失敗時は ROLLBACK を試行して例外を再送出。
    - API 失敗時は macro_sentiment=0.0 のフェイルセーフで継続。

- リサーチ & ファクター (kabusys.research)
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離 (ma200_dev) を計算。データ不足時は None。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。データ不足時は None。
    - calc_value: raw_financials から最新財務（report_date <= target_date）を取得し PER/ROE を算出。EPS が 0/欠損の時は per を None。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定 horizon（デフォルト [1,5,21]）に対する将来リターンを一度のクエリで取得（LEAD を利用）。
    - calc_ic: スピアマンのランク相関（IC）を実装。有効レコード数が 3 未満なら None。
    - rank: 同順位は平均ランクとする実装（丸め処理で ties 判定を安定化）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリ。

- データ基盤 (kabusys.data)
  - calendar_management モジュール:
    - JPX カレンダー管理用ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar テーブルがない場合は曜日ベースのフォールバック（週末は休場）を利用。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) により無限ループ回避。
    - calendar_update_job: J-Quants API から差分取得 → market_calendar へ冪等保存。バックフィル日数、健全性チェック（過度な将来日付はスキップ）を備える。
  - pipeline / ETL:
    - ETLResult データクラスを導入（取得件数 / 保存件数 / 品質問題 / エラー等を集約）。
    - ETL の設計方針（差分更新、backfill、品質チェックは収集して呼び出し元に委ねる）を反映。
  - etl のインターフェース再エクスポート（kabusys.data.etl が ETLResult を再エクスポート）。

### 変更 (Changed)

- なし（初回リリースのため過去変更は無し）

### 修正 (Fixed)

- なし（初回リリースのため修正履歴は無し）

### セキュリティ (Security)

- 機密情報を環境変数経由で取得する設計:
  - J-Quants、Kabu API、LINE、OpenAI のトークン/パスワードは環境変数を必須または任意で取得。未設定の場合は明示的にエラー（ValueError）を出す箇所あり（Settings._require、score_news/score_regime の API キー解決）。
- .env 読み込み時の protected ロジックにより既存 OS 環境変数が上書きされないよう保護。

### 既知の制約・注意点 (Notes)

- 日付/時刻の扱い:
  - 多くの処理で target_date を明示的に受け取り、内部で datetime.today()/date.today() を参照しない設計（ルックアヘッドバイアス防止）。ただし calendar_update_job はバッチ処理のため date.today() を利用。
  - news_window 等は JST を基準に計算し、DB 側の raw_news.datetime は UTC naive（設計前提）。
- OpenAI 依存:
  - デフォルトモデルは gpt-4o-mini。JSON Mode（response_format={"type": "json_object"}）を使う前提。
  - レスポンスのフォーマットや SDK のバージョン差異による挙動変化の可能性あり（APIError.status_code の有無に対する耐性を実装）。
  - API 呼び出し部分はテスト用に差し替え可能（_call_openai_api の patch）。
- DuckDB 互換性:
  - executemany に空リストを渡すと失敗するバージョンに対応するガードを導入。
  - 日付型の取り扱いで DuckDB の返り値を date に変換するユーティリティがある。
- フェイルセーフ:
  - LLM/API 障害時はエラーを直接上位に投げず、中立スコア（0.0）やチャンクスキップで継続する設計。DB 書き込み失敗時はトランザクションでロールバックを試みた上で例外を伝播。
- モジュール結合の制御:
  - ai.regime_detector と ai.news_nlp の間でプライベート関数を共有しない（それぞれ独自の _call_openai_api 実装など）。

### 将来対応が望まれる点（提案）

- OpenAI SDK の将来的な仕様変更に備えた互換ラッパーや統一的なレスポンス変換層の導入。
- 時刻帯管理を厳密化（UTC-aware datetime の導入）して DB 側とアプリ側の齟齬を完全排除。
- unit/integration テストのサンプル（DuckDB のインメモリやモック OpenAI クライアント）を整備して CI に組み込み。
- パフォーマンス計測・メトリクス露出（ETL パイプラインや OpenAI 呼び出しのレイテンシ計測）。

---

[Unreleased]: https://example.com/compare/HEAD...v0.1.0
[0.1.0]: https://example.com/releases/tag/v0.1.0

（注: 上記リンクはプレースホルダです。実際のリポジトリ URL に置き換えてください。）