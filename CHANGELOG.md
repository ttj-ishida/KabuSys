CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用しています。
https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（なし）

0.1.0 - 2026-04-04
------------------

Added
- パッケージ初期リリース:
  - kabusys パッケージの公開エントリポイントを追加（src/kabusys/__init__.py）。サブパッケージ data, research, ai, ... をエクスポート。
- 環境変数 / 設定管理:
  - Settings クラスを実装（src/kabusys/config.py）。J-Quants / kabuステーション / LINE / DB / 監視関連などの設定をプロパティとして提供。
  - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。読み込み優先順位は OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env パーサーの実装（クォート、エスケープ、export プレフィックス、インラインコメント等の取り扱いに対応）。環境変数保護（既存 OS 変数の上書き回避）機能あり。
  - 必須キー取得用のヘルパー _require を提供（未設定時は ValueError）。
  - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値チェック）実装。
- AI（自然言語処理）:
  - ニュースセンチメント解析モジュールを追加（src/kabusys/ai/news_nlp.py）。
    - raw_news / news_symbols を銘柄ごとに集約し、OpenAI（gpt-4o-mini）へバッチで問い合わせて銘柄毎の ai_score を ai_scores テーブルへ書き込み。
    - タイムウィンドウの計算（JSTベース → UTC比較）を実装（calc_news_window）。
    - バッチサイズ、記事数/文字数上限、JSON mode のレスポンス検証、リトライ（429/ネットワーク/タイムアウト/5xx）を実装。
    - レスポンス検証で不正応答はスキップするフェイルセーフ設計。
    - API 呼び出し部分はテストしやすく差し替え可能（_call_openai_api を patch 可能）。
  - 市場レジーム判定モジュールを追加（src/kabusys/ai/regime_detector.py）。
    - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュースの LLM センチメント（30%）を合成して日次で 'bull'/'neutral'/'bear' を判定。
    - DuckDB の prices_daily/raw_news/market_regime を参照し、冪等に market_regime テーブルへ書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API リトライ、フェイルセーフ（API失敗時は macro_sentiment=0.0）等の堅牢化処理を実装。
- データプラットフォーム（Data）:
  - カレンダー管理モジュールを追加（src/kabusys/data/calendar_management.py）。
    - market_calendar テーブルを参照して営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を提供。
    - DB 登録がない場合は曜日ベースでフォールバックする一貫した挙動を実装。探索上限を設けて無限ループを防止。
    - JPX カレンダー差分取得バッチ（calendar_update_job）を実装（J-Quants クライアント呼び出しと冪等保存、バックフィル、健全性チェック）。
  - ETL パイプライン基盤を追加（src/kabusys/data/pipeline.py、etl.py）。
    - ETLResult データクラスを実装して ETL の取得/保存件数、品質問題、エラーを集約。
    - 差分更新、バックフィル、品質チェックのための基本ロジックと設計方針を実装（J-Quants クライアント経由での取得／保存想定）。
- リサーチ（Research）:
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Volatility（20日ATR、相対ATR）、Value（PER、ROE）等の計算関数を実装。
    - DuckDB の SQL を利用して効率的に集計。データ不足時は None を返す設計。
  - 特徴量探索モジュールを追加（src/kabusys/research/feature_exploration.py）。
    - 将来リターン計算（calc_forward_returns）、IC（Spearman の ρ）計算、ランク化ユーティリティ、ファクター統計サマリーを実装。
    - pandas 等に依存せず、標準ライブラリおよび DuckDB クエリで完結する実装。
- ロギングと診断:
  - 各モジュールに詳細なログ（info/debug/warning）を追加。エラー発生時の挙動（例外伝播／フェイルセーフ）を明確化。
- テスト利便性:
  - OpenAI 呼び出し等を簡単にモックできる設計（内部 _call_openai_api を patch 可能）を採用。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Notes / Migration / Requirements
- 必要ランタイム依存:
  - duckdb, openai パッケージ等が必要（OpenAI API を利用する機能を使う場合）。
- 環境変数:
  - 主な環境変数:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - OPENAI_API_KEY（news_nlp / regime_detector で使用。api_key 引数で上書き可能）
    - KABUSYS_ENV（development, paper_trading, live のいずれか）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - DUCKDB_PATH / SQLITE_PATH 等のデフォルトパスは Settings で確認可能
  - .env の自動ロードはプロジェクトルートを基準に行われます。挙動を無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB スキーマ前提:
  - 各処理は DuckDB 上の特定テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）を参照/更新します。実行前に該当テーブルが存在することを確認してください。
- 設計方針・注意点:
  - ルックアヘッドバイアス回避のため、すべての時刻ロジックは target_date 引数に依存し、date.today()/datetime.today() を直接参照しない設計になっています。
  - OpenAI/API 呼び出しは堅牢にリトライやフェイルセーフを行い、不可逆的なデータ消失を避けるため部分的な失敗はスキップして継続する方針です。
  - news_nlp と regime_detector で OpenAI 呼び出し部分は意図的に分離されており、モジュール間でプライベート関数を共有しません（独立したテスト可能性の確保）。

今後の予定（アイデア）
- ai モジュールの追加モデル・パラメータ調整の提供
- ETL のスケジューリング / 実行管理ツールとの統合
- 追加のファクター・ポートフォリオ構築ロジックと backtest モジュール
- より詳細な DB スキーマ定義とマイグレーションスクリプト

貢献・報告
- バグ報告、機能要望、ドキュメント改善は Issue を作成してください。