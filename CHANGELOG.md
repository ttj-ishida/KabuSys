Keep a Changelog 準拠の形式で、コード内容から推測して作成した CHANGELOG.md（日本語）を以下に示します。

# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に従います。  

## [Unreleased]
- （現在の開発中の変更や予定の改良はここに記載）

## [0.1.0] - 2026-03-27
初回リリース。パッケージのコア機能とデータ処理・研究・AI連携の基盤実装を含む。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0、主要サブパッケージをエクスポート）。
- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード実装（プロジェクトルートを .git / pyproject.toml から探索）。
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト時の制御用）。
  - .env パーサ実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い等に対応）。
  - 環境変数上書きロジック（.env、.env.local の優先度と protected OS 環境変数保護）。
  - Settings クラスによりアプリケーション設定値をプロパティで提供（J-Quants / kabuステーション / Slack / DB パス / 環境判定 / ログレベル等）。
  - 環境値の妥当性検証（KABUSYS_ENV、LOG_LEVEL の検査）。
- データモジュール（kabusys.data）
  - market_calendar の管理と営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
  - カレンダーの夜間差分更新ジョブ（calendar_update_job）を実装。J-Quants からの差分取得と冪等保存、バックフィル・健全性チェックを含む。
  - ETL パイプラインのインターフェース（ETLResult の公開再エクスポート）。
  - ETL パイプライン本体（kabusys.data.pipeline）：
    - 差分取得・保存・品質チェックのフローに対応。
    - ETLResult データクラスによる実行結果集約（品質問題のサマリ・エラー判定メソッド含む）。
    - DuckDB を用いた最大日付取得やテーブル存在チェック等のユーティリティ。
- 研究（Research）モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）:
    - calc_momentum：1M/3M/6M リターン、200 日 MA 乖離等の算出。
    - calc_volatility：20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等。
    - calc_value：PER / ROE（raw_financials と prices_daily を組み合わせて算出）。
    - 実装は DuckDB SQL ベースで、欠損やデータ不足時の扱いを明確化。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - calc_forward_returns：複数ホライズンの将来リターンを一括取得できる処理。
    - calc_ic：Spearman ランク相関（IC）を計算するユーティリティ（欠測値除外、最小サンプル数チェック）。
    - rank：同順位は平均ランクにするランク化ユーティリティ（丸めによる ties 対応）。
    - factor_summary：各ファクターの count/mean/std/min/max/median を算出する統計要約。
  - 研究 API をパッケージとしてエクスポート（各種関数の再エクスポートを提供）。
- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）:
    - raw_news と news_symbols を集約し銘柄ごとにテキストを連結して LLM（gpt-4o-mini, JSON Mode）へ送信。
    - バッチ処理（最大 20 銘柄／リクエスト）、1 銘柄あたりの最大記事数・文字数トリム。
    - 429 / ネットワーク断 / タイムアウト / サーバ 5xx に対する指数バックオフリトライ実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出・results 配列・既知コードのみ・数値変換・有限値検査）。
    - スコアは ±1.0 にクリップし、ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT、部分失敗時に既存データを保護）。
    - テスト用に _call_openai_api を patch 可能（依存注入しやすい設計）。
  - 市場レジーム判定（kabusys.ai.regime_detector）:
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次のレジーム（bull/neutral/bear）を判定。
    - マクロキーワードに基づくタイトル抽出、OpenAI 呼び出し（gpt-4o-mini）によるマクロセンチメント評価、リトライ・フェイルセーフ（API 失敗時は 0.0）を実装。
    - レジームスコアを market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - AI 呼び出しは内部実装で分離（news_nlp とのプライベート関数共有を避ける）。
- 設計方針・品質面
  - ルックアヘッドバイアス対策：AI モジュール・研究関数は datetime.today()/date.today() を内部で参照しない（外部から target_date を与える方式）。
  - DuckDB を主要な永続層として利用（SQL と Python の組合せで効率的に集計・ウィンドウ関数を使用）。
  - ロギング、警告、例外処理、ROLLBACK の試行などエラーハンドリングと監査用ログ出力を重視。
  - テスト容易性のため、API 呼び出し箇所にモック差し替えフックを用意。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは明示的に引数から渡すことが可能（api_key 引数）で、環境変数依存を緩めテストや運用での漏洩リスクを制御しやすくしている。
- 環境変数の自動ロードは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

注意:
- 本 CHANGELOG は提供されたコードベースから推測して記載しています。実際のリリースノートやドキュメントはプロジェクトの意図や履歴に合わせ適宜修正してください。