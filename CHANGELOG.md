Keep a Changelog に準拠した CHANGELOG.md（日本語）
※コードベースから推測した変更点・機能説明を記載しています。

全般
-----
- 本リポジトリは KabuSys 日本株自動売買システムの初期リリースを表します。
- 内部的に DuckDB をデータストアとして利用し、J-Quants / kabuステーション / OpenAI を主な外部依存に想定しています。
- 設計方針として「ルックアヘッドバイアスの排除」「DBへの冪等（idempotent）書き込み」「API障害時のフェイルセーフ（例：ゼロフォールバック）」が一貫して採用されています。

フォーマットの使用法
-------------------
この CHANGELOG は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠しています。

[0.1.0] - 2026-04-01
--------------------
Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージエントリポイント: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートを .git または pyproject.toml で探索して .env/.env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化可能）。
    - .env パーサは export 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理などに対応。
    - 上書きロジック（.env は既存環境変数を保護、.env.local は上書き可能）と保護キー（OS環境変数群）を導入。
  - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス / 監視設定 / システム設定（KABUSYS_ENV, LOG_LEVEL）などのプロパティを定義。
    - 必須環境変数取得時は未設定で ValueError を送出する _require 実装。
    - KABUSYS_ENV および LOG_LEVEL の値検証を実装（許容値チェック）。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols テーブルを集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）の JSON モードでセンチメントを取得。
    - バッチ処理（1回につき最大 20 銘柄）、記事トリム（最大記事数・最大文字数制限）、429/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - レスポンスのバリデーション（JSON 抽出、results リスト、code/score の検証、数値変換、±1.0 にクリップ）を行い、ai_scores テーブルへ冪等的に書き込む（DELETE→INSERT）。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能（_call_openai_api を patch 可能）。
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を参照しない設計（target_date 指定方式）。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照して ma200_ratio を算出、マクロ記事はマクロキーワードでフィルタして LLM に投げる。
    - OpenAI 呼び出しに対するリトライ・バックオフ、API 失敗時の macro_sentiment = 0.0 フェイルセーフを実装。
    - 最終結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）する。
    - LLM 呼び出し部分もテストで差し替えられる設計。

- Data / ETL / カレンダー (src/kabusys/data)
  - ETL インターフェース (src/kabusys/data/etl.py, pipeline.py)
    - ETLResult データクラスを導入（取得件数、保存件数、品質チェック結果、エラー一覧などを保持）。
    - 差分取得・バックフィル・品質チェック・冪等保存を想定したパイプライン構造を実装。
    - DuckDB を前提としたテーブル存在チェックや最大日付取得ユーティリティを実装。
  - 市場カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルを元に営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない、または該当日が未登録の場合は曜日ベース（土日）でフォールバック。
    - calendar_update_job を実装し、J-Quants クライアントから差分取得して market_calendar を冪等保存。バックフィル・健全性チェックを実装。
    - 最大探索日数・先読み日数・バックフィル日数等の定数により安全性を確保。

- Research（因子・特徴量探索） (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum: 約1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算（データ不足時は None）。
    - Volatility: 20日 ATR（true range を正確に扱う）、ATR比率、20日平均売買代金、出来高比率等を計算。
    - Value: raw_financials から最新財務データを取得し PER / ROE を計算（EPS 0 または欠損時は None）。
    - 全て DuckDB 上の SQL + Python で完結し、本番取引 API にはアクセスしない設計。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算（calc_forward_returns）: target_date から指定ホライズンの終値リードを使いリターンを算出。horizons の検証あり。
    - IC（Information Coefficient）計算（calc_ic）: factor_records と forward_records を code で照合し Spearman（ランク相関）を算出。必要最小レコード数チェックあり。
    - ランキングユーティリティ（rank）、ファクター統計サマリ（factor_summary）を実装。
    - pandas 等の外部依存を避け、標準ライブラリのみで実装。

- テスト容易性・設計上の配慮
  - OpenAI 呼び出しなど外部依存部分に対して差し替え・モックが可能な設計（内部関数を patch しやすい命名/分離）。
  - ルックアヘッドバイアス防止のため日付参照を明示的な target_date ベースに統一。
  - API 障害時は例外を全面的に投げず、ログに記録して安全側の値（0.0/中立/スキップ）で継続する挙動が多くの箇所で採用。

Changed
- 初版につき該当なし（新規導入のみ）。

Fixed
- 初版につき該当なし。

Security
- 初版につき該当なし。

Notes / Known limitations
- OpenAI API の使用は gpt-4o-mini を想定しており、API レスポンスのフォーマット（JSON mode）を前提にしています。実運用では API 料金・レート制限や応答仕様の変更に注意が必要です。
- ETL / カレンダー / AI スコア保存処理はいずれも DuckDB の executemany の挙動（空パラメータ不可等）に配慮した実装が行われていますが、実際の DuckDB バージョン差異で微調整が必要になる可能性があります。
- 本 CHANGELOG はコードベースから推測して作成しています。実際のリリースノート（運用上の注意やマイグレーション手順など）は別途補足することを推奨します。

作者・貢献
--------------
- コード内の設計方針・コメントに基づく推測記載のため、実作者情報は省略しています。

（以上）