# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog 準拠の書式を採用しています。  
安定リリースのみを記載し、日付はリリース日を示します。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティ関連

※このログはソースコードの内容から推測して作成しています。

## [Unreleased]

- なし

---

## [0.1.0] - 2026-04-03

### Added
- パッケージ初期リリース: kabusys 0.1.0
  - Python パッケージのエントリポイントを定義（src/kabusys/__init__.py）。
- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に自動検出）。
  - export KEY=val 形式やクォート／エスケープを考慮した .env パース機能を実装。
  - OS 環境変数を保護する protected オプション、上書き制御（override）を実装。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
  - アプリケーション設定を Settings クラスとして公開（J-Quants / kabu API / LINE / DB パス / 監視設定 / システム設定）。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）を実装。
- AI モジュール（src/kabusys/ai）
  - ニュース NLP スコアリング（score_news）を実装（src/kabusys/ai/news_nlp.py）。
    - J-Quants で取得した raw_news / news_symbols を銘柄ごとに集約し、OpenAI（gpt-4o-mini）へ JSON モードで送信してセンチメントを取得。
    - バッチ処理（最大 20 銘柄/リクエスト）、記事トリム、スコアクリッピング（±1.0）、レスポンス検証を実装。
    - 429／ネットワーク断／タイムアウト／5xx に対する指数バックオフリトライ実装。フェイルセーフで失敗時はスキップ（例外非伝播）。
    - DuckDB への冪等書き込み（DELETE→INSERT）により部分失敗時も既存データを保護。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - 市場レジーム判定（score_regime）を実装（src/kabusys/ai/regime_detector.py）。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次のレジーム（bull/neutral/bear）を判定。
    - prices_daily, raw_news, market_regime を使用し、DB への冪等書き込みを行う（BEGIN/DELETE/INSERT/COMMIT）。
    - LLM コールは news_nlp と独立した実装とし、モジュール間結合を避ける設計。
    - API エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフを実装。
- Data モジュール
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを利用した営業日判定 API（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を提供。
    - DB データがない場合は曜日（土日）ベースのフォールバックを行う一貫性ロジックを実装。
    - JPX カレンダーを J-Quants から差分取得して安全に更新する夜間バッチ（calendar_update_job）を実装。バックフィルと健全性チェックを実装。
  - ETL / パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを追加（ETL の取得数・保存数・品質チェック結果・エラーを収集）。
    - 差分更新、バックフィル、品質チェックのためのユーティリティ（jquants_client と quality モジュール連携を想定）。
- Research（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER/ROE）、Volatility（20日 ATR）、Liquidity（20日平均売買代金、出来高比）を実装。
    - DuckDB のウィンドウ関数を活用した効率的な SQL ベース実装。
    - データ不足時は None を返す仕様で安全性を重視。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（任意ホライズン対応）、IC（Spearman）計算 calc_ic、ランク変換 rank、統計サマリー factor_summary を実装。
    - pandas など外部依存なしで実装。
  - 研究用ユーティリティの再エクスポートを提供（__init__）。
- パッケージ公開インターフェース
  - data.pipeline.ETLResult を data.etl から再エクスポート（使い勝手向上）。
  - ai、research、data パッケージの主要関数を __all__ で明示的に公開。

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

### Security
- 環境変数と API キーの取り扱いに注意:
  - OpenAI API キーは関数引数経由で注入可能（テスト時に明示的に指定可能）。また環境変数 OPENAI_API_KEY を参照する実装。
  - .env の自動ロードは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Notes / 設計上の重要点
- 全体に共通する設計方針:
  - ルックアヘッドバイアス回避のため、内部で datetime.today() / date.today() を勝手に参照しない（target_date を明示的に渡す設計）。
  - OpenAI など外部 API 呼び出しはリトライとフェイルセーフを備え、単一失敗がシステム全体を停止させない。
  - DuckDB を主要なローカル分析 DB として利用。DB 書き込みは冪等性を重視（DELETE→INSERT 等）。
  - テスト容易性を考慮し、API 呼び出し部分は patch / モックしやすい抽象化を行っている。
- デフォルトのパスと閾値は Settings で管理（例: DUCKDB_PATH= data/kabusys.duckdb、監視閾値など）。
- calendar_management や ETL 周りは J-Quants クライアント実装（jquants_client）との連携を前提としているが、クライアントの具象実装は別モジュールで提供する想定。

---

（補足）この CHANGELOG は与えられたソースコードの内容とドキュメント文字列から推測して作成したものです。実際のコミット履歴やリリースノートと差異がある可能性があります。必要であれば、実際の Git 履歴やリリースポリシーに基づいて文言を調整します。