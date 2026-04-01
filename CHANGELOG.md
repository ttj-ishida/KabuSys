CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠し、セマンティックバージョニングを採用します。

フォーマット:
- Unreleased / バージョン / 日付
- 各バージョンごとに Added / Changed / Fixed / Security / その他の注意点 を記載

Unreleased
----------

（未リリースの変更はここに記載します）

[0.1.0] - 2026-04-01
-------------------

初期リリース。以下の主要機能・モジュールを実装・公開しました。

Added
- パッケージ初期化
  - kabusys パッケージ（__version__ = 0.1.0）を追加。公開 API として data, strategy, execution, monitoring をエクスポート。

- 環境設定 / ローディング（kabusys.config）
  - .env / .env.local ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルート検出は __file__ を基点に .git または pyproject.toml を探索するため、CWD に依存しない自動ロードを実現。
  - export KEY=val 形式やクォート・エスケープ、コメントの取り扱いに対応する .env パーサ実装。
  - 自動ロード無効化環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを導入し、J-Quants / kabuステーション / Slack / データベース / 監視 / システム設定のプロパティを提供（必須項目は _require で検証）。
  - KABUSYS_ENV（development, paper_trading, live）や LOG_LEVEL の検証を追加。

- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp.score_news
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini、JSON Mode）で銘柄ごとのセンチメントを算出して ai_scores テーブルへ書き込み。
    - 時間ウィンドウ計算（JSTベース→UTC変換）、チャンク処理（最大20銘柄）、記事トリム（記事数・文字数上限）を実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライとレスポンスの厳密なバリデーションを実装。
    - レスポンス中の余分なテキストへ対処するため JSON 抽出ロジックを含む。
    - テスト用に _call_openai_api をモック差し替え可能に設計。
    - 部分失敗時に既存の他銘柄スコアを保護するため、DELETE → INSERT の対象コード絞り込み方式で冪等書き込みを実装。

  - regime_detector.score_regime
    - ETF 1321（Nikkei 225 連動 ETF）の 200 日移動平均乖離（重み 70%）と、news_nlp によるマクロニュースセンチメント（重み 30%）を合成して market_regime テーブルへ日次で冪等保存。
    - LLM 呼び出しは gpt-4o-mini を利用、失敗時は macro_sentiment=0.0 のフォールバック（フェイルセーフ）。
    - OpenAI クライアント生成やエラーハンドリング・リトライ方針を明確化。
    - lookahead バイアス防止のため target_date 未満のみを参照するクエリ設計。

- Data / ETL / カレンダー（kabusys.data）
  - calendar_management
    - market_calendar の存在チェック、営業日判定（is_trading_day）、次/前営業日の取得（next_trading_day / prev_trading_day）、範囲内営業日取得（get_trading_days）、SQ日判定（is_sq_day）を実装。
    - DB 登録値優先・未登録日は曜日ベースでフォールバックする一貫したロジック。
    - 夜間バッチ更新 calendar_update_job を実装（J-Quants から差分取得して冪等保存、バックフィル・健全性チェック付き）。
  - pipeline / ETLResult
    - ETL 実行結果を表す dataclass (ETLResult) と、ETL パイプラインの骨組みを実装（差分取得・保存・品質チェック などの設計方針を反映）。
    - ETLResult.to_dict による品質問題の辞書化を実装。
  - etl モジュールで pipeline.ETLResult を再エクスポート。

- Research（kabusys.research）
  - factor_research
    - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials を参照して各種定量ファクター（モメンタム、MA200乖離、ATR、流動性、PER, ROE 等）を計算。
    - データ不足時は None を返す設計、結果は (date, code) 単位の dict リストで返却。
  - feature_exploration
    - calc_forward_returns（将来リターン計算、任意ホライズン対応）、calc_ic（Spearmanランク相関での IC 計算）、factor_summary（基本統計量）、rank（順位付け、同順位は平均ランク）を実装。
    - pandas など外部依存無しで実装。
  - research パッケージの __all__ に主要関数を公開。

- その他ユーティリティ
  - DuckDB を想定した SQL 実行設計。多くの関数は duckdb.DuckDBPyConnection を引数に取り、SQL + Python の組合せで計算を完結。
  - ロギング（logger）を各モジュールで活用し、処理状況やフォールバックを明示。

Security
- 環境変数として API キー・トークン（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を利用。これらは必須プロパティで未設定時は ValueError を送出して明示的に失敗する設計。
- .env 読み込みはデフォルトで有効。テスト用途に自動読み込みを無効化する機能を提供（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

Design / テストに有用な実装上の配慮
- ルックアヘッドバイアス防止: 日付判断・集計は target_date を明示的に渡す設計（date.today() や datetime.today() を参照しない）。
- OpenAI 呼び出し周りは内部関数をモックしやすく分離（unittest.mock.patch での差し替えを想定）。
- DB 書き込みは冪等設計（DELETE → INSERT／ON CONFLICT の方針）で部分失敗時のデータ保全を考慮。
- DuckDB のバージョン依存注意（executemany の空リスト禁止等）をコード内で回避するガードがある。

Known issues / 注意点
- 本バージョンは初期リリースのため、strategy / execution / monitoring の具体実装は別途（または外部モジュール）で提供される想定。パッケージ __all__ ではそれらを露出しているが、今回提供したファイル群にすべての実装が含まれているわけではありません。
- OpenAI API のレスポンスフォーマット依存（JSON mode）に対する堅牢化処理は実装しているが、LLM の挙動変化により追加対応が必要となる可能性があります。
- J-Quants / kabu API のクライアント実装（jquants_client 等）は参照されるが、本差分で提供されているかは実装状況によるため、実行時には外部クライアント実装と DB スキーマが必要です。
- 型ヒントに Python 3.10 以降の構文（X | Y）を使用しているため、実行環境は Python 3.10+ を推奨します。

ライセンス / 貢献
- 本 CHANGELOG はリポジトリ内の現行コードベースから推測して作成しています。実際の要件や API 仕様に合わせて随時追記・修正してください。

---