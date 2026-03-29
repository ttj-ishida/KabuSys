CHANGELOG
=========

このファイルは Keep a Changelog の方針に準拠して作成されています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- 今後のリリースでの変更点はここに記載します。

[0.1.0] - 2026-03-29
-------------------

初回リリース（初期実装）

Added
- パッケージ基盤
  - kabusys パッケージ初期実装。__version__ = "0.1.0" を設定し、主要サブパッケージを公開（data, research, ai, など）。
- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート判定は .git または pyproject.toml を探索して決定（cwd 非依存）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 読み込み順は OS 環境変数 > .env.local（上書き） > .env（未設定のみ）。
    - OS 側の既存環境変数は protected として上書きされない設計（安全対策）。
  - .env パーサーは export 形式、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等のプロパティを取得可能に。
  - env 値・ログレベルのバリデーションと、is_live / is_paper / is_dev のヘルパーを追加。
- AI 関連（kabusys.ai）
  - ニュース NLP（news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini、JSON Mode）でセンチメントを取得する score_news を実装。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたり記事数・文字数のトリム、JSON レスポンスのバリデーション、スコア ±1.0 クリップを実装。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ・リトライを実装。その他のエラーはスキップしてフェイルセーフ（処理継続）。
    - DuckDB への書き込みはトランザクションで行い、部分失敗時に既存スコアを保護するため code を絞って DELETE → INSERT を実行。
    - テスト容易性のため OpenAI 呼び出し部は内部で _call_openai_api を分離（unittest.mock.patch で差し替え可能）。
    - ニュース収集ウィンドウ（JST基準）計算ユーティリティ calc_news_window を提供。
  - 市場レジーム判定（regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - prices_daily から MA200 乖離を計算、raw_news からマクロキーワードでフィルタして記事を取得、LLM 評価（gpt-4o-mini JSON）で macro_sentiment を算出。
    - API 失敗時は macro_sentiment=0.0 を採用するフェイルセーフ設計。
    - 計算結果は market_regime テーブルへ冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT）。ロールバック時のログ出力を装備。
    - OpenAI 呼び出しはニュース NLP と独立した実装とし、モジュール結合を避ける。
- Research（kabusys.research）
  - factor_research: calc_momentum, calc_value, calc_volatility を実装。
    - Momentum: 約1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None を返す挙動）。
    - Value: raw_financials から最新財務を取得し PER / ROE を算出（EPS が 0/欠損時は None）。
    - Volatility: 20 日 ATR、相対 ATR、20 日平均売買代金・出来高比率などを計算。
    - すべて DuckDB クエリ中心で外部 API には依存しない設計。
  - feature_exploration: calc_forward_returns（任意ホライズンの将来リターンを一括取得）、calc_ic（Spearman ランク相関による IC 計算）、rank（同順位は平均ランク）、factor_summary（基本統計）を実装。
    - calc_forward_returns は horizons の入力検証（正の整数かつ <=252）と複数ホライズンを一度に取得する最適化を実装。
    - calc_ic はデータ不足（有効レコード < 3）で None を返す安全仕様。
- Data（kabusys.data）
  - calendar_management
    - market_calendar を基にした営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - market_calendar 未取得時は曜日ベース（土日非営業日）でフォールバック。
    - next/prev では DB 登録値を優先し、未登録日は曜日フォールバックで一貫性を保つ実装。最大探索範囲を設定して無限ループを防止。
    - calendar_update_job により J-Quants API から差分取得・バックフィル・健全性チェックを行い、冪等に保存する仕組みを実装（jq.fetch_market_calendar / jq.save_market_calendar を利用）。
  - pipeline / etl
    - ETLResult データクラスを実装（ETL 実行結果の集約、品質問題・エラー一覧の保持、辞書化ユーティリティ）。
    - 差分取得用の内部ユーティリティ（_get_max_date 等）を実装。J-Quants の差分更新・バックフィル設計に準拠。
  - jquants_client 経由での保存/取得を想定した実装（クライアントは別モジュールで提供）。
- 汎用設計方針・品質
  - ルックアヘッドバイアス防止: 各モジュールで date.today()/datetime.today() を直接参照せず、target_date を明示的に与える設計。
  - DuckDB 互換性のため、executemany に対する空リスト処理など実装上の注意点を反映。
  - ログ出力（info/debug/warning）を充実させ、失敗時もプロセス継続するフェイルセーフな挙動を採用。
  - テスト容易性のため外部 API 呼び出し箇所を分離してモック可能にしている箇所が複数存在。

Changed
- 初回公開のため該当なし。

Fixed
- .env パーサーの堅牢化（export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント処理など）による実運用での読み込み耐性向上。
- DuckDB 書き込みにおける空パラメータの扱いに関する互換性考慮（executemany の空リストを回避）。

Security
- 環境変数の自動ロード時に既存の OS 環境変数を保護する設計を採用（protected set）。  
- OpenAI API キー・各種トークンは Settings を介して必須チェックを行い、未設定時は明確なエラーを返す。

Known issues / Notes
- OpenAI API の利用は環境変数 OPENAI_API_KEY か関数引数での注入が必須。API キー未設定時は ValueError を送出する。
- JSON Mode を前提とするため LLM レスポンスに余計なテキストが混入する場合に備え、レスポンス復元（最外の {} を抽出）のロジックを実装しているが、全ケースを完全に保証するものではない。
- DuckDB のバージョン差異により一部の SQL バインド方法（ANY/リストバインド等）が不安定となるため、互換性の高い実装（個別 DELETE via executemany）を採用している。
- calendar_update_job 等は jquants_client の実装に依存するため、実運用では API クレデンシャルやネットワークの設定が必要。

---

今後のリリースでは以下を検討しています:
- エンドツーエンドの統合テストケース追加（外部 API モックを含む）
- ai モジュールの追加評価指標（信頼区間・説明可能性メタデータ等）
- カレンダー更新の並列化や ETL パフォーマンス改善

ご不明点や修正希望があれば issue を作成してください。