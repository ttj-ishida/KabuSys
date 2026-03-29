# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、Semantic Versioning を前提とします。

注: この CHANGELOG はリポジトリ内のコードから機能・挙動を推測して作成しています。実装済みの公開 API、環境変数、既定値、設計上の注意点などをまとめています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-29

Added
- パッケージ基盤
  - 初期リリースとして kabusys パッケージを追加。
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）。
  - __all__ に data, strategy, execution, monitoring を公開。

- 環境変数・設定管理（src/kabusys/config.py）
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途）。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）。
  - .env パーサーは以下をサポート:
    - コメント行、空行、`export KEY=val` 形式。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - クォート無しの値でのインラインコメント処理（直前がスペース/タブの場合のみ # をコメントと判定）。
  - Settings クラスを提供（settings = Settings()）。必須環境変数取得時は _require により未設定なら ValueError を発生。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須。
    - KABU_API_BASE_URL のデフォルトは "http://localhost:18080/kabusapi"。
    - DuckDB / SQLite のデフォルトパスを提供（DUCKDB_PATH, SQLITE_PATH）。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL（DEBUG/INFO/...）のバリデーション。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- AI（自然言語処理）モジュール（src/kabusys/ai）
  - ニュースセンチメント（銘柄単位）
    - score_news(conn, target_date, api_key=None)
      - raw_news / news_symbols を集約し、銘柄ごとに過去ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）内の記事を結合して OpenAI（gpt-4o-mini）へ送信。
      - バッチサイズ 20 銘柄、1 銘柄当たり最大記事数 10、最大文字数トリム（3000 文字）でトークン膨張を抑制。
      - JSON Mode を利用し、レスポンスを厳密な JSON として検証・抽出。スコアは ±1.0 にクリップ。
      - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライを実装し、それ以外は失敗時に当該チャンクをスキップ（フェイルセーフ）。
      - 成功した銘柄のみ ai_scores テーブルへ冪等的に置換（DELETE → INSERT）。
      - テスト容易性: 内部の OpenAI 呼び出し関数はモック差し替え可能（unittest.mock.patch を想定）。
  - マクロレジーム判定
    - score_regime(conn, target_date, api_key=None)
      - ETF 1321 の 200 日移動平均乖離 (MA200) と、マクロ経済ニュースの LLM センチメントを重み付け（MA 70%、マクロ30%）して市場レジーム（bull/neutral/bear）を日次判定。
      - MA の計算は target_date 未満のデータのみを使用しルックアヘッドバイアスを防止。
      - マクロ記事が存在しない場合は LLM 呼び出しを行わず macro_sentiment=0.0。
      - OpenAI 呼び出し失敗時は macro_sentiment=0.0 で継続（警告ログ）。
      - 計算結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書込失敗時は ROLLBACK を実施して上位へ例外を伝播。

- 研究（Research）モジュール（src/kabusys/research）
  - factor_research.py
    - calc_momentum(conn, target_date)
      - mom_1m / mom_3m / mom_6m、ma200_dev（200 日 MA に対する乖離）を計算。データ不足時は None を返す。
    - calc_volatility(conn, target_date)
      - atr_20（20 日 ATR の単純平均）、atr_pct、avg_turnover（20 日平均売買代金）、volume_ratio を計算。必要行数未満は None。
    - calc_value(conn, target_date)
      - raw_financials から直近財務データを取得して PER（EPS が 0 または欠損なら None）と ROE を計算。
  - feature_exploration.py
    - calc_forward_returns(conn, target_date, horizons=None)
      - デフォルト horizons は [1,5,21]。将来終値との差でリターンを計算。horizons の妥当性をチェック。
    - calc_ic(factor_records, forward_records, factor_col, return_col)
      - Spearman のランク相関（IC）をランク化して計算。有効レコードが 3 未満なら None。
    - rank(values) と factor_summary(records, columns)
      - ランク付け（同順位は平均ランク）、基本統計量（count/mean/std/min/max/median）を算出。
  - 研究ユーティリティは標準ライブラリのみで実装され、DuckDB を利用して高速な SQL ベース処理を行う設計。

- データプラットフォーム（src/kabusys/data）
  - calendar_management.py
    - JPX 市場カレンダー管理（market_calendar テーブル）を提供。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等の営業日判定ユーティリティを実装。
    - calendar_update_job(conn, lookahead_days=90) により J-Quants API から差分取得 → 市場カレンダーを冪等で保存（バックフィル・健全性チェックあり）。
    - DB にカレンダーが存在しない場合は曜日ベースのフォールバック（週末を非営業日とする）を採用。DB 登録値が優先され、未登録日はフォールバックで一貫した挙動。
    - 最大探索日数の上限設定（_MAX_SEARCH_DAYS）により無限ループを防止。
  - pipeline.py / etl.py
    - ETLResult データクラスを提供（ETL 実行結果の集約）。
    - ETL パイプラインの設計に基づく差分取得、保存、品質チェックのためのユーティリティ群の初期実装。
    - 差分取得時のバックフィル日数や品質チェックの取り扱い方針が実装に反映。
  - jquants_client / quality 系は外部モジュール（data.jquants_client 等）との連携を想定。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Deprecated
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Security
- OpenAI API の利用に際しては API キーを引数で注入可能（api_key 引数）か、環境変数 OPENAI_API_KEY を利用する仕様。未設定の場合は明確に ValueError を発生させるため誤使用を防止。

Notes / 注意事項
- ルックアヘッドバイアス対策
  - AI モジュール・研究モジュールともに datetime.today() / date.today() を直接参照しない設計。すべての計算は明示的な target_date に基づくため、将来データ参照を防止。
- フェイルセーフ
  - OpenAI 呼び出し失敗時は多くの場合フェイルセーフ（スコア 0.0 または該当チャンクスキップ）で処理を継続する設計。運用時はログを監視すること。
- テスト性
  - OpenAI 呼び出しや内部ユーティリティはモック差し替えを想定して作られているため、ユニットテストの注入が容易。
- 必須環境変数
  - 本リリースでは運用に必要な環境変数が複数存在するため、導入時は .env.example を参考に .env を準備すること（Settings._require により未設定時に例外が発生します）。
    - 必須例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（AI 機能使用時）
- デフォルトの DB パス
  - DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で変更可能）
  - SQLite (monitoring): data/monitoring.db（SQLITE_PATH で変更可能）

今後の予定（想定）
- strategy / execution / monitoring の具体的な自動発注ロジック・監視の実装拡充。
- jquants_client と品質チェック（quality）モジュールの詳細実装・統合テスト。
- OpenAI レスポンスの堅牢化・より詳細なプロンプト設計やモデル切替設定の導入。

---
（以上）