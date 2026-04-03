# Changelog

すべての注目すべき変更をこのファイルに記録します。
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) のフォーマットに従います。
バージョニングは SemVer を採用します。

## [Unreleased]
（未リリースの変更はここに記載します）

---

## [0.1.0] - 2026-04-03

初回公開リリース。日本株自動売買／データ基盤・リサーチ・AI支援のためのコア機能群を実装しました。
主に以下のサブパッケージと主要機能を追加しています。

### Added
- パッケージ基盤
  - pakage エントリポイント: `kabusys.__init__` を追加（__version__ = 0.1.0、公開モジュール: data, strategy, execution, monitoring）。
- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動ロードする仕組み（プロジェクトルート検出: .git / pyproject.toml ベース）。
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
  - .env のパース機能（コメント、export 形式、クォート・エスケープ処理に対応）。
  - Settings クラスによりアプリ設定をプロパティ経由で提供（J-Quants / kabu ステーション / LINE / DB パス / 監視閾値 / ログレベル等）。
  - 必須環境変数未設定時は明示的な例外を送出する `_require`。

- データプラットフォーム（src/kabusys/data）
  - ETL パイプライン基盤
    - ETL 実行結果表現 `ETLResult`（`kabusys.data.pipeline.ETLResult` を `kabusys.data.etl` で再公開）。
    - 差分取得、バックフィル、品質チェックの設計に基づくパイプラインロジック（pipeline モジュールの主要ユーティリティを含む）。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダーの夜間バッチ更新ジョブ `calendar_update_job` を実装（J-Quants クライアント経由で差分取得 → 冪等保存）。
    - 営業日判定・探索ユーティリティ群: `is_trading_day`, `is_sq_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days` を提供。
    - DB データがない/未登録日の場合は曜日ベースのフォールバックを採用。
    - 最大探索範囲（安全装置）やバックフィル、健全性チェック実装。
  - jquants_client / quality 等の外部クライアントを利用する設計（jquants_client の fetch/save 呼び出しを想定）。

- リサーチ（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日MA乖離）。
    - Volatility / Liquidity: 20日 ATR（atr_20 / atr_pct）、avg_turnover、volume_ratio。
    - Value: PER（price / EPS）、ROE（raw_financials から最新レコードを結合）。
    - 全関数は DuckDB 接続を受け取り SQL を用いて計算。出力は (date, code) を含む dict のリスト。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算 `calc_forward_returns`（任意ホライズン、既定: [1,5,21]）。
    - IC（Information Coefficient）計算 `calc_ic`（Spearman の ρ をランク相関で計算）。
    - ランク変換ユーティリティ `rank`（同順位は平均ランク、浮動小数点丸め対策あり）。
    - 統計サマリー `factor_summary`（count/mean/std/min/max/median）。
  - 研究用ユーティリティを `kabusys.research.__init__` で公開（主要関数の再エクスポート）。

- AI 支援機能（src/kabusys/ai）
  - ニュースセンチメント（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとのニュースを生成、OpenAI（gpt-4o-mini）へバッチ投げしてセンチメントスコアを算出。
    - 時間ウィンドウ（前日15:00 JST〜当日08:30 JST）を正しく UTC に変換して照合する `calc_news_window` を提供。
    - バッチサイズ制限、記事数/文字数トリム、JSON Mode レスポンスの堅牢なパース、レスポンス検証（results リスト・code/score の型チェック）、スコアクリップを実装。
    - リトライ戦略: 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ。
    - idempotent な DB 書き込み（取得した銘柄のみ DELETE → INSERT）を実装。
    - テスト用に `_call_openai_api` をパッチ差し替え可能。
    - パブリック API: `score_news(conn, target_date, api_key=None)`（返り値: 書込銘柄数）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出はキーワードベース（リスト定義）でタイトルを取得 `_fetch_macro_news`。
    - OpenAI 呼び出しは独立実装 `_call_openai_api`（news_nlp と共有しないことでモジュール結合を低減）。
    - API 安全装置: リトライ、5xx とそれ以外の分岐、パース失敗・API失敗時は macro_sentiment=0.0 にフォールバック。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - パブリック API: `score_regime(conn, target_date, api_key=None)`（返り値: 1 成功）。

- その他
  - DuckDB を想定した SQL 実装（接続オブジェクトを受け取り純粋に DB 上で計算／更新を行う設計）。
  - ロギングと警告の充実（データ不足、パースエラー、API エラー等で適切にログ出力）。
  - テストしやすい設計（OpenAI 呼び出しを差し替え可能、設定の自動ロードは環境変数で無効化可能など）。

### Security
- API キーの取り扱いは環境変数経由を推奨（OpenAI: `OPENAI_API_KEY`、J-Quants: `JQUANTS_REFRESH_TOKEN`、kabu: `KABU_API_PASSWORD`）。
- .env 自動読み込みはプロジェクトルート検出に基づき行われ、必要に応じて無効化可能（`KABUSYS_DISABLE_AUTO_ENV_LOAD`）。

### Design / Behavior Notes（設計上の重要点）
- ルックアヘッドバイアス防止: すべての date ベース処理は内部で datetime.today() / date.today() を参照しない。target_date に対して厳密に過去データのみを使用するよう設計。
- フェイルセーフ: 外部 API 失敗時は基本的に例外を投げず（ただし API キー未設定などは例外）、可能な限り処理を継続して安全側の値（0.0 やスキップ）を使う。
- DB 書き込みは冪等性を重視（DELETE → INSERT、ON CONFLICT を想定した保存）。
- DuckDB のバージョン差異（executemany の空パラメータ制約など）を考慮した実装。

### Known Limitations / Not Implemented
- 一部の指標（PBR、配当利回りなど）は現バージョンでは未実装（calc_value に注記あり）。
- news_nlp/news_regime の出力は LLM に依存するため、LLM の品質によりスコアの信頼性が変動する。
- jquants_client / kabusys.data.jquants_client の実装はこの変更セットに含まれていない前提（外部クライアントを呼び出す設計）。

---

今後のリリースでは以下を検討しています:
- strategy / execution / monitoring の具体実装（発注ロジック・監視ループ）。
- テストカバレッジの拡充、CI 統合。
- PBR 等追加ファクター、モデル学習パイプラインの統合。

（必要であれば、この CHANGELOG を基により細かいコミット単位の履歴を生成します。どの粒度がよいか指示してください。）