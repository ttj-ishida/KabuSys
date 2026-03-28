CHANGELOG
=========

すべての注記は Keep a Changelog の形式に準拠しています。  
このプロジェクトはまだ若く、以下はコードベースの内容から推測した初回リリース（および今後の未リリース予定）に関する変更履歴です。

Unreleased
----------

- 今後の予定／検討事項（コードベースから推測）
  - strategy / execution / monitoring パッケージの具体実装追加
  - ETL パイプラインのジョブスケジューリングと運用監視のサンプル
  - テストカバレッジ拡充（ユニットテスト・統合テスト）
  - ドキュメント（API / 使用例 / デプロイ手順）の整備

[0.1.0] - 2026-03-28
--------------------

初期リリース — 基本的なデータ処理、研究用ユーティリティ、ニュース NLP と市場レジーム判定の実装を含む

Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0、公開サブパッケージ定義）
- 設定管理
  - kabusys.config
    - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して特定）
    - export KEY=val、クォート・エスケープ、インラインコメントなどを考慮した .env パーサー実装
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
    - Settings クラスで環境変数をラップ（必須項目取得 _require, バリデーション、デフォルト値）
    - 環境値検証: KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL に対する厳格チェック
    - DB ファイルパス（DUCKDB_PATH / SQLITE_PATH）のデフォルトと expanduser 処理
- AI 関連（ニュース NLP / レジーム判定）
  - kabusys.ai.news_nlp
    - raw_news / news_symbols を集約して銘柄ごとのニューステキストを作成
    - OpenAI（gpt-4o-mini）へバッチ送信（最大バッチサイズ 20）
    - JSON Mode レスポンスの検証・パース（結果の正規化と ±1.0 へクリップ）
    - 429 / ネットワークエラー / タイムアウト / 5xx に対する指数バックオフリトライ
    - DuckDB への冪等書き込み（DELETE → INSERT、部分失敗時に既存データを保護）
    - テスト用に OpenAI 呼び出し関数の差し替えが可能（モックしやすい設計）
    - calc_news_window ユーティリティ（JST 時間ウィンドウと UTC 変換）
  - kabusys.ai.regime_detector
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、ニュース由来の LLM センチメント（重み 30%）を組合せて日次で市場レジーム（bull/neutral/bear）を判定
    - OpenAI（gpt-4o-mini、JSON Mode）呼び出し、再試行、フォールバック（失敗時 macro_sentiment=0.0）
    - DuckDB を用いた ma200_ratio / raw_news の取得、および market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - レジーム算出式と閾値の定義
- リサーチ（ファクター計算・特徴量探索）
  - kabusys.research.factor_research
    - モメンタム: mom_1m/mom_3m/mom_6m、ma200_dev（不足データ時は None）
    - ボラティリティ/流動性: 20日 ATR（atr_20 / atr_pct）、avg_turnover、volume_ratio（データ不足時は None）
    - バリュー: PER（EPS が 0 または欠損時は None）、ROE（raw_financials から最新レコード）
    - DuckDB を活用した SQL ベースの実装（外部 API へアクセスしない）
  - kabusys.research.feature_exploration
    - 将来リターン（calc_forward_returns: 任意ホライズン、horizons の検証）
    - IC（calc_ic: スピアマンランク相関、欠損/同順位処理）
    - ランク変換ユーティリティ（rank: 平均ランク処理、丸め対策）
    - ファクター統計サマリー（count/mean/std/min/max/median）
- データ管理・ETL
  - kabusys.data.calendar_management
    - market_calendar テーブルを使った営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
    - カレンダー未取得時は曜日ベースのフォールバック
    - calendar_update_job により J-Quants から差分取得して冪等に保存（バックフィル、健全性チェック）
  - kabusys.data.pipeline, kabusys.data.etl
    - ETLResult dataclass による ETL 実行結果表現（品質問題・エラー一覧を含む）
    - 差分取得ロジック、最終取得日判定、バックフィル、DuckDB テーブル存在チェック等のユーティリティ
    - jquants_client / quality モジュールと連携することを前提とした設計
  - kabusys.data パッケージに ETLResult の再エクスポート
- テスト性・堅牢性向上
  - OpenAI 呼び出しをモジュール内関数でまとめ、テスト時に patch 可能（ユニットテスト容易化）
  - DB 書き込みでトランザクション管理（ROLLBACK の試行と失敗時の警告）
  - 入出力（JSON）パースエラーは例外ではなくログ出力してフェールセーフで継続
  - 多数のログメッセージ（info/debug/warning/exception）を付与

Changed
- （初回リリースのため該当なし、実装上の設計方針を明文化）
  - ルックアヘッドバイアス回避のため、内部処理は date.today() を直接参照しない設計が徹底されている点を明記

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数読み込みにおいて OS 環境変数を保護（.env の上書き制御: protected set を利用）
- API キーやトークンは Settings 経由で必須チェックを行い、未設定の場合は明示的なエラーを返す

Compatibility / Requirements（推測）
- Python 3.10+（型注釈に X | Y 構文を使用しているため）
- duckdb パッケージ
- openai（OpenAI Python SDK）パッケージ
- jquants_client（外部モジュール／プラグイン、DataPlatform 用）
- 環境変数（例）
  - OPENAI_API_KEY（AI 機能を使う際に必須）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - KABUSYS_ENV, LOG_LEVEL（任意だが検証あり）
  - DUCKDB_PATH, SQLITE_PATH（デフォルトあり）

移行メモ / 注意点
- OpenAI を使う機能（score_news, score_regime）は API キーが必須。テスト環境では api_key 引数で注入可能。
- .env の自動読み込みはプロジェクトルート検出（.git / pyproject.toml）を基に行われる。CI/テストで不要なら KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。
- DuckDB における executemany の制約（空リスト不可）に対応するため、空の params の場合は DB 操作をスキップする実装がある。
- レスポンスパースや API エラーはフォールバック（0.0 スコアやスキップ）で安全に動作する設計だが、精度向上のためは OpenAI モデルの安定供給と適切なプロンプト設計が必要。

貢献 / 報告
- バグ報告、機能提案、ドキュメント改善のプルリクエストを歓迎します。README / CONTRIBUTING（未実装）の整備を今後検討しています。

--- 

注: 上記は現行ソースコードの構造・コメント・関数名・設計方針から推測して作成した CHANGELOG です。リリース日や一部の実装意図は推測に基づきます。必要であれば実際のコミット履歴やリリースノートに合わせて日付・変更内容を調整します。