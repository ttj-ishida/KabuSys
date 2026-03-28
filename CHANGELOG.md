# Changelog

すべての変更は Keep a Changelog の仕様に準拠します。  
このファイルは、リポジトリ内のソースコードから推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-28

### Added（追加）
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開情報:
    - src/kabusys/__init__.py によりバージョン __version__ = "0.1.0" を設定。
    - パッケージ外部公開名: data, strategy, execution, monitoring（ただし monitoring は今リリースでの実装ファイルは含まれていない可能性あり）。

- 環境設定モジュール（src/kabusys/config.py）
  - .env/.env.local の自動ロード機能（プロジェクトルートの検出は .git または pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサーは以下をサポート:
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理
    - クォートなしでのインラインコメント取り扱い（直前が空白/タブの場合に # をコメントとして扱う）
  - 環境設定管理クラス Settings を提供（settings インスタンスをエクスポート）。
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティを公開:
      - jquants_refresh_token, kabu_api_password, kabu_api_base_url
      - slack_bot_token, slack_channel_id
      - duckdb_path（デフォルト data/kabusys.duckdb）, sqlite_path（デフォルト data/monitoring.db）
      - env（development / paper_trading / live の検証）および log_level の検証
      - is_live / is_paper / is_dev ヘルパー

- AI（自然言語処理）モジュール（src/kabusys/ai）
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を用いてニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを評価して ai_scores テーブルへ書込む。
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（UTC に変換して比較）。
    - バッチ処理: 最大 _BATCH_SIZE=20 銘柄単位で API 呼び出し。
    - 1銘柄あたり _MAX_ARTICLES_PER_STOCK=10 件、最大文字数 _MAX_CHARS_PER_STOCK=3000 によるトリム。
    - エラー耐性: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフのリトライ実装。
    - レスポンス検証: JSON 抽出、"results" キーの存在・型検証、コード整合性チェック、数値性チェック。スコアは ±1.0 にクリップ。
    - DB 書込は冪等性を考慮（対象コードのみ DELETE → INSERT）し、DuckDB の executemany 空リスト制約に対処。
    - テストフック: _call_openai_api を unittest.mock.patch で差し替え可能。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。

  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - マーケットレジーム判定（'bull' / 'neutral' / 'bear'）を日次で算出し market_regime テーブルへ書込む。
    - 指標:
      - ETF 1321 の 200 日移動平均乖離（重み 70%）
      - マクロニュースの LLM（gpt-4o-mini）センチメント（重み 30%）
    - 処理フロー:
      - calc_news_window を利用してニュースウィンドウを算出（news_nlp と互換）。
      - DuckDB からデータを取得し、MA200 乖離やマクロ記事タイトルを抽出。
      - OpenAI 呼び出しは独立実装。API エラー時は macro_sentiment=0.0 として継続（フェイルセーフ）。
      - レジームスコア合成後、冪等に market_regime テーブルへ書込（BEGIN / DELETE / INSERT / COMMIT）。DB 書込失敗時は ROLLBACK。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。

- Data（データプラットフォーム）モジュール（src/kabusys/data）
  - calendar_management（src/kabusys/data/calendar_management.py）
    - JPX カレンダー管理と営業日判定ユーティリティを提供。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（週末を非営業日）を使用。
    - calendar_update_job(conn, lookahead_days=90) により J-Quants から差分取得して market_calendar を冪等更新。バックフィルと健全性チェック（未来日付の異常検知）を実装。
    - jquants_client（kabusys.data.jquants_client）経由での fetch/save を想定。

  - ETL / pipeline（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETL の結果を表すデータクラス ETLResult を実装（target_date / fetched/saved counts / quality_issues / errors 等）。
    - 差分取得、保存、品質チェックの方針とユーティリティを実装するための基盤関数群（テーブル存在チェック、最大日付取得、トレーディングデイ補正など）。
    - data.etl モジュールで ETLResult を再エクスポート。

- Research（リサーチ）モジュール（src/kabusys/research）
  - factor_research（src/kabusys/research/factor_research.py）
    - モメンタム、ボラティリティ、バリュー等の定量ファクター計算を実装:
      - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m / ma200_dev（200 日ウィンドウが不足する場合は None）
      - calc_volatility(conn, target_date): atr_20, atr_pct, avg_turnover, volume_ratio（必要行数不足は None）
      - calc_value(conn, target_date): per（EPS が無効時 None）, roe（raw_financials の最新レコードを結合）
    - DuckDB を用いて SQL ベースで計算。外部 API へのアクセスは行わない。

  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=None)（デフォルト [1,5,21]）
      - horizons の妥当性チェック（正整数かつ <= 252）
      - 一度のクエリで複数ホライズンを取得する実装
    - IC（Information Coefficient）計算: calc_ic(factor_records, forward_records, factor_col, return_col)（スピアマンのランク相関）
      - サンプル数不足（<3）や分散ゼロ時は None を返す
    - ランク変換ユーティリティ: rank(values)（同順位は平均ランク）
    - 統計サマリー: factor_summary(records, columns)（count/mean/std/min/max/median を計算）
    - 研究系は本番トレード系 API にアクセスしない設計

- ロギング・エラーハンドリング
  - 各モジュールに詳細な logger 呼び出し（info/warning/debug/exception）を追加。
  - OpenAI 呼び出しまわりでのリトライロジックと、パース失敗時の安全フォールバック（スコア 0.0）の実装。

### Changed（変更）
- （初期リリースのため該当なし）

### Fixed（修正）
- （初期リリースのため該当なし）

### Deprecated（非推奨）
- （初期リリースのため該当なし）

### Removed（削除）
- （初期リリースのため該当なし）

### Notes（注意点 / 既知の設計上の制約）
- OpenAI API の使用箇所は api_key を引数で注入可能（テスト容易性のため）。api_key が未設定の場合は環境変数 OPENAI_API_KEY を参照し、未設定なら ValueError を送出する。
- ニュース集約およびレジーム判定はルックアヘッドバイアスを避ける設計（datetime.today()/date.today() を内部で参照しない）。target_date に対して過去のデータのみを使用。
- DuckDB バージョンに依存する注意点（executemany に空リストを与えられない等）に対してガードコードを追加。
- 一部モジュール（例: monitoring）の実装ファイルが今回の抜粋に含まれていない可能性があるため、外部公開名は将来の実装に依存。
- .env パーサーは多くのケースをカバーするが、非常に特殊な .env フォーマットでは挙動に差異が出る可能性あり。

---

この CHANGELOG はソースからの静的解析に基づいて作成しています。実際のコミット履歴・リリースノートと差異がある可能性があるため、リリース時は git の履歴や CHANGELOG の最終化を行ってください。