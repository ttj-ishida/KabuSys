Keep a Changelog
=================
この CHANGELOG は Keep a Changelog の形式に準拠しています。  
重要な変更点のみを記載しています。日付・バージョンはコードベースの内容から推測して付与しています。

Unreleased
----------

（現在未リリースの変更はありません）

[0.1.0] - 2026-03-28
-------------------

Added
- 初回公開: KabuSys パッケージ（src/kabusys）
  - パッケージ公開情報: __version__ = "0.1.0"、主要サブパッケージを __all__ で公開 (data, strategy, execution, monitoring)。
- 設定/環境変数管理 (src/kabusys/config.py)
  - .env ファイルの自動読み込み機能を実装（優先度: OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応（テスト用）。
  - .env 行パーサーは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱いに対応。
  - 環境変数保護（既存 OS 環境変数を保護する protected セット）を考慮した読み込み。
  - Settings クラスを実装: J-Quants / kabu ステーション API、Slack、データベースパス（duckdb/sqlite）、実行環境（development/paper_trading/live）やログレベルの検証、is_live/is_paper/is_dev ヘルパー等を提供。
  - 必須環境変数未設定時は明示的なエラーを返す _require を提供。
- データレイヤ / ETL (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py, src/kabusys/data/__init__.py)
  - ETL パイプラインのインターフェースを追加。ETLResult データクラスを公開（取得/保存件数、品質問題、エラー集約、診断用 to_dict）。
  - 差分更新、バックフィル、品質チェック、id_token 注入でのテスト容易性など設計方針を実装。
  - DuckDB との互換性考慮（テーブル未存在チェック、最大日付取得ユーティリティなど）。
- マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
  - market_calendar を前提とした営業日判定ロジックを実装:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
  - カレンダー未取得時は曜日ベース（平日のみ営業）でのフォールバック。
  - calendar_update_job を実装（J-Quants API から差分取得、バックフィル、健全性チェック、冪等保存）。
  - 最大探索日数やバックフィル期間、サニティチェック等の安全策を導入。
- AI: ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols を元に OpenAI（gpt-4o-mini）で銘柄ごとにセンチメントを算出し ai_scores テーブルへ書き込む処理を実装。
  - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）、銘柄ごとの記事集約、最大記事数/文字数トリム、最大バッチサイズ 20（_BATCH_SIZE）でのバッチ送信に対応。
  - OpenAI 呼び出しのリトライ（429, ネットワーク断, タイムアウト, 5xx）および指数バックオフを実装。
  - JSON Mode での厳密なレスポンス処理と復元ロジック（前後余計なテキストが混じる場合の {} 抽出）。
  - スコアの検証・クリップ（±1.0）、非数値/未知コードの扱い、取得済みコードのみを DELETE→INSERT で置換して部分失敗を保護する書き込み戦略。
  - テスト用の差し替えポイント (_call_openai_api) を用意。
  - API 未設定時には明示的な ValueError を送出。
- AI: 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225連動型）200日移動平均乖離を用いる ma200_ratio と、マクロ経済ニュースの LLM センチメントを合成して日次の市場レジーム（'bull'/'neutral'/'bear'）を判定する score_regime を実装。
  - マクロキーワードによる raw_news フィルタ、OpenAI（gpt-4o-mini）呼び出し、エラー時のフェイルセーフ（macro_sentiment=0.0）、再試行ロジックを実装。
  - スコア合成の重み付け（MA 70% / マクロ 30%）やしきい値を定義し、冪等的に market_regime テーブルへ書き込む。
  - テスト用差し替えポイントと OpenAI API 呼び出しの独立実装を採用（モジュール結合を避ける設計）。
- Research（src/kabusys/research/*）
  - ファクター計算: calc_momentum, calc_value, calc_volatility を実装（prices_daily / raw_financials を参照）。
    - Momentum: mom_1m/mom_3m/mom_6m、ma200_dev（データ不足は None）。
    - Value: PER/ROE（最新財務データとの組合せ）。
    - Volatility: 20日 ATR / 相対 ATR、20日平均売買代金、出来高比率等。
  - 特徴量探索: calc_forward_returns（任意ホライズンに対する将来リターンの一括取得）、calc_ic（Spearman ランク相関による IC）、rank（同順位は平均ランク扱い）、factor_summary（count/mean/std/min/max/median）を実装。
  - 外部ライブラリ非依存・DuckDB 経由の実装、ルックアヘッドバイアス防止の方針を採用。
- その他ユーティリティ
  - DuckDB 用の互換性考慮（executemany に対する空リスト回避、日付変換ユーティリティ等）。
  - ロギングを多用し、例外時に情報を残す設計。

Changed
- —（本バージョンは初回公開のため、過去バージョンからの変更はありません）

Fixed
- —（初回公開のため該当なし）

Security
- 環境変数ロード時に OS 環境変数を保護する設計（.env による上書きは保護対象を除外）。
- OpenAI API キー未設定時の明確なエラーにより誤設定を早期検出。

Design / 注意点（ドキュメント的な補足）
- 全てのアルゴリズムで datetime.today() / date.today() を直接参照しない方針（ルックアヘッドバイアス回避）。外部から target_date を注入して評価する設計。
- OpenAI 呼び出しは JSON Mode を使用し、API レスポンスのパース失敗や API 障害はフェイルセーフで扱い（0.0 フォールバックやスキップ）、長期運用での堅牢性を重視。
- DuckDB に依存する SQL 実装のため、環境に合わせた DuckDB バージョン互換性（executemany の挙動など）に注意。
- テスト容易性のため、外部呼び出し（OpenAI や J-Quants クライアント）を注入または patch 可能な実装。

既知の制限 / TODO（コードから推測）
- PBR・配当利回り等一部バリューファクターは未実装（calc_value の注記）。
- strategy / execution / monitoring の具体実装ファイルは本リリースでは参照される公開 API の一部として名前空間に含まれるが、詳細な実装が別途存在する可能性あり（本 CHANGELOG は現在のコードベースから推測）。
- calendar_update_job は J-Quants クライアント側の実装（fetch_market_calendar, save_market_calendar）に依存するため、外部 API の応答形式変更に注意。

署名
- 作成日: 2026-03-28（コードベースの日付・内容から推測）