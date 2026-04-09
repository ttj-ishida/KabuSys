# Changelog

すべての重要な変更をここに記載します。  
このファイルは "Keep a Changelog" の形式に従い、セマンティックバージョニングを採用します。

現在の安定版: 0.1.0

## [Unreleased]

## [0.1.0] - 2026-04-09
初回リリース。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を導入。
  - パッケージトップで公開するサブパッケージ: data, strategy, execution, monitoring（__all__ にてエクスポート）。
- 設定 / 環境変数管理（kabusys.config）
  - .env/.env.local の自動ロード機能を実装。プロジェクトルートは .git または pyproject.toml を基準に探索するため、CWD に依存しない動作。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ等に対応）。
  - Settings クラスを導入し、以下の設定値をプロパティ経由で取得可能に：
    - J-Quants / kabuステーション / LINE / DB パス（duckdb/sqlite）関連設定
    - Paper Trading 関連（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）
    - 監視関連（PID ファイル、Kill Flag、リソース閾値）
    - 環境（KABUSYS_ENV）・ログレベル（LOG_LEVEL）と検証
    - is_live, is_paper, is_dev のユーティリティプロパティ
  - 必須環境変数未設定時には ValueError を発生させる _require 実装。
- AI 関連（kabusys.ai）
  - news_nlp モジュール（kabusys.ai.news_nlp）:
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON mode を用いてセンチメントを評価。
    - バッチ処理（最大 20 銘柄 / リクエスト）、1 銘柄あたりの記事数・文字数の制限、レスポンス検証、スコアの ±1.0 クリップを実装。
    - リトライ（429, ネットワーク断, タイムアウト, 5xx） は指数バックオフで実行。部分失敗に対する DB 保護（影響を受けたコードのみ上書き）を考慮。
    - ニュースウィンドウ定義（JST 基準の前日 15:00 〜 当日 08:30 を UTC に変換）と calc_news_window ユーティリティを提供。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能に実装（_call_openai_api を patch 可能）。
  - regime_detector モジュール（kabusys.ai.regime_detector）:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と news_nlp によるマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - LLM 呼び出しは独立実装、失敗時は macro_sentiment=0.0 のフェイルセーフ。
    - OpenAI API の再試行・5xx 判定とバックオフ、JSON レスポンスパースの耐性を実装。
    - DuckDB を用いた冪等な market_regime テーブル書き込み（BEGIN / DELETE / INSERT / COMMIT）。
  - 両モジュールとも gpt-4o-mini を利用し、JSON モードを期待する厳格なパースとフォールバック挙動を持つ。
- データ関連（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）:
    - ETLResult データクラスを導入（取得件数、保存件数、品質問題リスト、エラーリスト等を保持）。
    - 差分更新、バックフィル、品質チェック（quality モジュール）を想定した設計。
    - ETLResult に to_dict / has_errors / has_quality_errors 等のユーティリティを提供。
  - ETL の公開インターフェース（kabusys.data.etl）として ETLResult を再エクスポート。
  - マーケットカレンダー管理（kabusys.data.calendar_management）:
    - market_calendar テーブルを使った営業日判定、next/prev_trading_day、get_trading_days、is_sq_day を実装。
    - DB データがない場合の曜日ベース（週末除外）フォールバック。
    - calendar_update_job により J-Quants API からの差分取得・バックフィル・健全性チェックを実装（保存は jquants_client へ委譲）。
    - 最大探索日数・バックフィル日数・将来の日付の健全性チェック等を用意。
- リサーチ / ファクター（kabusys.research）
  - factor_research:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、平均売買代金、出来高比）、Value（PER、ROE）などの定量ファクター計算を実装。
    - DuckDB 上の SQL を用いた計算で、欠損やデータ不足時の None 返却等の扱いを明確化。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、rank、factor_summary などの統計解析ユーティリティを提供。
    - pandas 等の外部依存を持たず標準ライブラリのみで実装。
  - research パッケージは zscore_normalize（kabusys.data.stats）を含むユーティリティと合わせて公開。
- DB / API クライアント想定
  - DuckDB を主要なオンメモリ／ファイル DB として利用する設計。
  - jquants_client 等の外部クライアントモジュールを組み合わせる想定（calendar ETL 等で使用）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （初回リリースのためセキュリティ修正はなし）
- 注意点: OpenAI API キー等のシークレットは環境変数から取得する設計。.env 自動ロードの挙動を理解した上で運用すること。

### Design / Implementation Notes（重要な設計判断）
- ルックアヘッドバイアス回避:
  - datetime.today() / date.today() をスコアリング・ETL 内で直接参照しない設計を採用。すべての関数は target_date を明示的に受け取る。
  - prices_daily クエリなどは target_date 未満（排他）や LEAD/LAG を用いて未来データを参照しないように注意。
- API 呼び出しの堅牢性:
  - OpenAI 呼び出しは RateLimit / 接続断 / タイムアウト / 5xx に対して再試行・指数バックオフを実装し、最終的に安全なフォールバック（スコア=0.0 やスキップ）を行う。
- DB 書き込みの冪等性:
  - market_regime / ai_scores などは該当日・該当コードを明示的に削除してから挿入することで冪等性を確保（部分失敗時に他データを保護）。
- テスト容易性:
  - OpenAI 呼び出しを行う内部関数（_call_openai_api）についてはユニットテストで差し替え可能な形に実装。
- DuckDB 互換性:
  - executemany に空リストを渡せない等の制約に対する回避を実装。

### Breaking Changes
- 初回リリースのためなし。

---

注: 本 CHANGELOG は現行コードベースの内容から推測して作成しています。実際のリリースノート作成時はコミット履歴・issue 等を参照のうえ必要に応じて追記・修正してください。