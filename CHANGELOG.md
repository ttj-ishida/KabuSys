# Changelog

全ての重要な変更は Keep a Changelog の形式に従って記載しています。  
現在のバージョンは src/kabusys/__init__.py に定義された v0.1.0 です。

注意: 下記はコードベースから推測して作成した初回リリースの変更履歴です。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-01

### Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ情報:
    - __version__ = "0.1.0"
    - パッケージ公開 API: data, strategy, execution, monitoring を __all__ で公開

- 環境・設定管理モジュール (kabusys.config)
  - .env / .env.local ファイルと OS 環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）
  - 読み込み順序: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサ実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメント処理（クォートあり/なしの挙動を分けて解釈）
  - Settings クラスで各種設定をプロパティとして提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - データベースパス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（data/monitoring.db）
    - 監視設定: PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（デフォルト値あり）
    - システム: KABUSYS_ENV のバリデーション（development / paper_trading / live）、LOG_LEVEL のバリデーション
  - 必須環境変数未設定時は _require が ValueError を送出して明示的に失敗する

- AI 関連モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI (gpt-4o-mini, JSON mode) にバッチ送信してセンチメントを算出
    - 処理の特徴:
      - JST ベースのニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）
      - 1 銘柄あたり最大記事数・最大文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）
      - 1 API コールで最大 20 銘柄を処理（チャンク化）
      - レート制限(429)、ネットワーク断、タイムアウト、5xx に対する指数バックオフとリトライ
      - レスポンスの厳格なバリデーション（JSON 抽出、results 配列、code と score の型チェック、スコア ±1.0 にクリップ）
      - データベースへの書き込みは冪等性を考慮（対象コードのみ DELETE → INSERT）し、部分失敗時も既存スコアを削らない設計
      - テスト容易性のため _call_openai_api をパッチで差し替え可能
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジームを判定（'bull' / 'neutral' / 'bear'）
    - 処理の特徴:
      - DuckDB の prices_daily, raw_news, market_regime テーブルを使用
      - ma200_ratio の計算は target_date 未満のデータのみを使用（ルックアヘッドバイアス防止）
      - マクロキーワードでニュースを抽出し、OpenAI (gpt-4o-mini) に JSON 出力を要求して macro_sentiment を取得
      - API エラー・パースエラーは macro_sentiment=0.0 にフォールバック（フェイルセーフ）
      - リトライ/バックオフロジックを実装
      - market_regime テーブルへの書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等に実行

- データ処理モジュール (kabusys.data)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを参照して営業日判定を提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - カレンダーデータがない場合は曜日ベースでフォールバック（週末を非営業日扱い）
    - calendar_update_job 実装: J-Quants API から差分を取得して market_calendar を冪等に更新（バックフィル・健全性チェックあり）
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを実装して ETL 結果（取得件数、保存件数、品質問題、エラーなど）を集約
    - 差分更新、バックフィル、品質チェック（quality モジュール）を想定した設計
    - pipeline の ETLResult を kabusys.data.etl から再エクスポート

- リサーチモジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算
    - calc_value: per（株価/EPS）、ROE を raw_financials と prices_daily から算出
    - 実行は DuckDB 内の SQL + Python で行い、外部 API に依存しない設計
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン後のリターン（複数ホライズン対応、デフォルト [1,5,21]）
    - calc_ic: スピアマンランク相関（IC）を計算
    - rank: 平均ランク（同順位は平均ランク）変換
    - factor_summary: カラムごとの count/mean/std/min/max/median を計算
  - これらはすべて prices_daily / raw_financials テーブルの参照に限定

### Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で提供する設計。未設定時は ValueError を出して明示的に失敗させる（誤動作防止）。

### Notes / 設計上の注意点
- ルックアヘッドバイアス防止: AI モジュールおよびリサーチ関数で datetime.today()/date.today() を直接参照しない設計。すべて target_date を明示的に与えることで再現性を担保。
- データベース操作: DuckDB を前提に SQL を記述。executemany に空リストを渡せないバージョン（例: DuckDB 0.10）への互換性を考慮した実装（空チェックあり）。
- フェイルセーフ: 外部 API エラーやパースエラーは基本的に例外を投げずにフォールバック（例: macro_sentiment=0.0、該当チャンクスキップ）することで長期バッチ運用での継続性を優先。
- テスト性: OpenAI 呼び出し部分はモジュール内で専用関数化してあり、ユニットテスト時に差し替え可能（unittest.mock.patch など）。

### Changed
- 初回リリースのため該当なし

### Fixed
- 初回リリースのため該当なし

### Deprecated
- 初回リリースのため該当なし

---

参照: 実装に基づく想定動作・設計方針を CHANGELOG に反映しています。実際のリリース日や追加の変更はリポジトリのリリース運用に合わせて更新してください。