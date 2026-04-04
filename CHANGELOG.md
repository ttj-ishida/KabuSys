CHANGELOG
=========

この CHANGELOG は「Keep a Changelog」フォーマットに準拠しています。  
コードベースから推測できる主な追加・変更点を日本語で記載しています。

記載方針:
- 日付は本ファイル作成日（2026-04-04）を使用しています。
- 実装の設計方針やフェイルセーフ挙動など、コードから読み取れる重要な挙動も注記しています。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-04
-------------------

Added
- パッケージ基盤
  - kabusys パッケージの公開 API を定義（__version__ = 0.1.0、data/strategy/execution/monitoring をエクスポート候補として宣言）。
- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD 非依存）。
    - 読み込み順: OS 環境変数 > .env.local (> .env)。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメントなどに対応。
  - 必須環境変数取得のヘルパ（_require）と Settings クラスを提供。
    - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等のキーをラップしてプロパティから取得可能。
  - 各種設定のデフォルト値（API ベース URL、データベースパス、監視しきい値、ログレベルなど）を定義。
  - KABUSYS_ENV の検証（development / paper_trading / live）とログレベル検証を実装。
- データプラットフォーム（kabusys.data）
  - calendar_management モジュール
    - JPX マーケットカレンダー管理（market_calendar）と営業日判定ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB 登録値を優先し、未登録日は曜日ベースのフォールバックを使用する一貫した挙動を採用。
    - 夜間バッチ calendar_update_job を実装（J‑Quants から差分取得して idempotent に保存）。
    - 健全性チェック（将来日付やバックフィル処理）を実装。
  - pipeline / etl モジュール
    - ETLResult データクラスを公開（etl パイプラインの実行結果を集約）。
    - 差分取得・バックフィル・品質チェックを行う設計（jquants_client と quality モジュール連携を想定）。
    - DuckDB との互換性（executemany 空リスト回避等）を考慮した実装。
- 研究（research）モジュール
  - factor_research
    - モメンタム（1M/3M/6M）、200日MA乖離、ATR（20日）等のファクター計算を実装（prices_daily, raw_financials を参照）。
    - 各関数は DuckDB 接続を受け取り SQL + Python で計算し、(date, code) をキーとする dict のリストを返す。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - Spearman（ランク相関）を算出する IC ロジック、欠測・有限値チェックを含む堅牢な実装。
  - research パッケージの再エクスポートを提供（主要関数を __all__ で公開）。
- AI（kabusys.ai）
  - news_nlp
    - raw_news + news_symbols を集約し、OpenAI（gpt-4o-mini）により銘柄ごとのセンチメント（ai_score）を生成して ai_scores テーブルへ保存する処理を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算を提供（calc_news_window）。
    - バッチ処理（最大20銘柄/リクエスト）、スコアクリップ、トークン過大対策（記事トリム）、レスポンスバリデーション等を実装。
    - リトライ戦略（429/ネットワーク断/5xx/タイムアウトに対する指数バックオフ）を備える。
    - テスト容易性のため _call_openai_api を外部でモック可能に設計。
  - regime_detector
    - ETF 1321 の 200 日 MA 乖離（重み70%）とニュース由来のマクロセンチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定、market_regime テーブルへ冪等書き込みを行う処理を実装。
    - マクロ記事抽出、OpenAI 呼び出し、合成スコア計算、閾値判定、DB トランザクション（BEGIN/DELETE/INSERT/COMMIT）まで含む。
    - API エラー時は macro_sentiment=0 としてフォールバック（フェイルセーフ）。
    - news_nlp と同様、OpenAI 呼び出しを独立実装しモジュール結合を避ける設計。
- ユーティリティ・互換性
  - DuckDB を想定した SQL 実装（information_schema、window 関数、executemany の取り扱いなど）。
  - OpenAI SDK（OpenAI クライアント）との統合を想定した抽象化を行い、API レスポンスの JSON Mode を用いる。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 環境変数依存の機密情報（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、OPENAI_API_KEY 等）は Settings を通じて明示的に取得。自動 .env ロードは無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

設計上の重要な注意点（コードからの読み取り）
- ルックアヘッドバイアス回避
  - いずれのスコアリング・ファクター計算でも datetime.today()/date.today() を直接参照せず、呼び出し側から target_date を受け取る設計を採用。
  - DB クエリでは target_date 未満（排他）や date = ? といった条件により未来情報の参照を防止。
- フェイルセーフ
  - 外部API（OpenAI, J‑Quants）呼び出しが失敗した場合でも例外を投げずフォールバック（スコア0.0や処理スキップ）する箇所が多く、全体の継続性を優先する設計。
- 冪等性 / 部分失敗耐性
  - データ書き込みは DELETE→INSERT や ON CONFLICT 相当の手法で冪等に行う。
  - ai_scores などは更新対象のコードを絞って書き換えることで部分失敗時に既存データを保護。
- テスト容易性
  - OpenAI 呼び出し部分（_call_openai_api）をパッチ可能にしてユニットテストでモックしやすくしている。
- DuckDB の互換性考慮
  - executemany に空リストを渡さないチェックや情報スキーマ参照における注意点が盛り込まれている。

依存（コードから推測）
- duckdb
- openai（OpenAI SDK）
- 標準ライブラリ（datetime, json, logging, os, pathlib, time 等）

備考
- 本 CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノート作成時は実装者の追加情報（実際のリリース日、マイグレーション手順、既知の制約など）を反映してください。