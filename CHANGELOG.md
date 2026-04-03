Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。リポジトリに含まれるコードから推測できる変更点・初期リリース内容をまとめています。

なお日付は現在（2026-04-03）をリリース日として記載しています。必要に応じて日付や文言を調整してご利用ください。

――――――――――――――――――――――――――――――
CHANGELOG.md
――――――――――――――――――――――――――――――

Keep a Changelog
=================
すべての注目すべき変更はこのファイルに記録します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
- （未リリースの変更はここに記載します）

0.1.0 - 2026-04-03
-----------------
Added
- パッケージ基盤
  - kabusys パッケージ公開インターフェースを定義（__version__ = 0.1.0）。
  - パッケージレベルで data, strategy, execution, monitoring を外部公開（__all__）。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索して行うため、CWD に依存しない。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサを実装（クォート文字列、バックスラッシュエスケープ、インラインコメント、export プレフィックス等に対応）。
  - override/protected オプションを持つ .env 読み込みで OS 環境変数を保護。
  - Settings クラスを提供し、各種設定値（J-Quants, kabu, LINE, DB パス, 監視しきい値, ログレベル等）をプロパティ経由で取得。
    - 必須設定値が未定義の場合は ValueError を送出する _require を用意。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値外は ValueError）。
    - Path 型でのパス展開（expanduser）や bool/float の変換処理を実装。

- データプラットフォーム / カレンダー管理（kabusys.data.calendar_management）
  - market_calendar を用いた営業日判定ロジックを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB 登録データを優先し、未登録日は曜日（土日）ベースでフォールバックする一貫した動作。
    - 最大探索日数や健全性チェック（将来日付の異常検出）など安全対策を実装。
  - calendar_update_job を実装（J-Quants API から差分取得し冪等に保存、バックフィル対応）。

- ETL パイプライン（kabusys.data.pipeline / etl）
  - ETLResult データクラスを公開（kabusys.data.etl 経由で再エクスポート）。
    - ETL 実行結果（取得件数・保存件数・品質チェック結果・エラー一覧）を集約。
    - has_errors / has_quality_errors / to_dict 等のユーティリティを実装。
  - 差分更新・バックフィル・品質チェック方針をコード内で実装（J-Quants クライアント呼び出し・保存は jquants_client を利用想定）。
  - DuckDB を想定したテーブル存在チェックと最大日付取得ユーティリティを実装。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を用いた銘柄別のニュースセンチメントスコアリング機能を実装。
    - タイムウィンドウ計算（JST 前日 15:00 ～ 当日 08:30 相当の UTC 変換）。
    - 銘柄ごとに最新記事を集約（記事数・文字数上限でトリム）。
    - OpenAI（gpt-4o-mini）へバッチ送信（最大 BATCH_SIZE 銘柄）し JSON Mode でレスポンスを期待。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - レスポンスのバリデーション（JSON 抽出、results 配列、code/score の整合性、数値チェック）、スコアを ±1.0 にクリップ。
    - 成功した銘柄のみ ai_scores テーブルに置換的（DELETE → INSERT）に書き込むことで部分失敗時の保護を実現。
  - テスト容易性を考慮し、内部の OpenAI 呼び出し (_call_openai_api) を unittest.mock.patch でモック可能に設計。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する機能を実装。
    - ma200_ratio の計算は target_date 未満のデータのみを使用（ルックアヘッドを防止）。
    - マクロキーワードで raw_news をフィルタしてタイトルを抽出し、OpenAI により macro_sentiment を算出（記事が無ければ LLM 呼び出しをスキップし 0.0 を使用）。
    - OpenAI 呼び出しはリトライ/バックオフや 5xx の扱いを考慮し、失敗時は macro_sentiment=0.0 でフェイルセーフ継続。
    - 合成スコアをクリップし閾値でラベル付け、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。

- リサーチ（kabusys.research）
  - factor_research：
    - calc_momentum: mom_1m / mom_3m / mom_6m と ma200_dev（200日MA乖離）を計算。
    - calc_volatility: 20日 ATR（atr_20）, 相対 ATR（atr_pct）, 20日平均売買代金, volume_ratio を計算。
    - calc_value: raw_financials から最新財務データを取得し PER/ROE を算出（EPS が 0/欠損時は None）。
    - DuckDB の SQL を駆使して効率的に集計（営業日ベースの窓計算）する設計。
  - feature_exploration：
    - calc_forward_returns: 指定基準日から各 horizon（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: ファクター値と将来リターンのランク相関（Spearman ρ）を計算。データ不足（有効レコード < 3）時は None を返却。
    - rank / factor_summary: ランク変換（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を計算するユーティリティを提供。
  - すべてのリサーチ関数は外部 API を呼ばず、prices_daily / raw_financials 等の DB テーブルのみ参照する方針。

Security / Reliability / Design notes
- ルックアヘッドバイアス対策として、target_date ベースで過去データのみを参照し、datetime.today()/date.today() を直接使わない設計を多くのモジュールで採用。
- OpenAI 呼び出しに対するリトライ・バックオフ、レスポンスパースの堅牢化（余分なテキストから JSON を抽出するロジック等）を実装。
- DB 書き込みは冪等性を意識（DELETE→INSERT、ON CONFLICT を想定）し、トランザクションと ROLLBACK を適切に処理。
- テスト容易性: API 呼び出し部分を差し替え可能にする設計（内部関数をモック可能）。

Notes
- 各モジュール内に詳細な docstring と設計方針を含む。実装は DuckDB を前提とした SQL 実行と Python ロジックの組合せで構築されている。
- OpenAI クライアント（OpenAI(api_key=...)）を直接使用するため、実行環境にて OPENAI_API_KEY の設定が必要（各関数は api_key 引数で注入可能）。
- package の公開 API に strategy / execution / monitoring が含まれるが、ここに示されていない実装はリポジトリの他ファイルに存在する想定（必要に応じて CHANGELOG を更新してください）。

――――――――――――――――――――――――――――――

必要があれば、次の変更点テンプレート（Unreleased 例、マイナーバージョン/パッチリリースの書式）も用意できます。どの粒度で記録したいか（コミット単位／機能単位／チケット単位）を教えてください。