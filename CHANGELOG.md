CHANGELOG
=========

すべての重要な変更を追跡します。本ファイルは Keep a Changelog のフォーマットに準拠します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-04-01
--------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムのコアモジュール群を追加。
  - パッケージ公開情報
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
    - パッケージ外部公開モジュール列挙: data, strategy, execution, monitoring（パッケージ構成の骨子を提供）
  - 環境設定
    - 環境変数/設定管理モジュールを実装 (src/kabusys/config.py)
      - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化
      - .env のパースは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱いに対応
      - .env と OS 環境変数の優先順位制御（.env.local は .env を上書き、OS 環境変数は保護）
      - Settings クラスにアプリ設定を集約（J-Quants / kabu API / Slack / DB パス / 監視閾値 / システム環境判定等）
      - 設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）
  - AI（自然言語処理 / レジーム判定）
    - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
      - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出
      - JST基準のニュースウィンドウ計算（前日15:00 JST ～ 当日08:30 JST を UTC に変換）
      - バッチ処理（最大 20 銘柄 / チャンク）、1銘柄当たりの記事数・文字数上限でトークン肥大化に対処
      - API 呼び出し: JSON Mode を利用、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ
      - レスポンス検証ロジック: JSON 抽出、"results" 構造検査、未知コード無視、数値変換と ±1.0 のクリップ
      - DB への冪等書き込み（対象コードの DELETE → INSERT、部分失敗時は既存スコア保護）
      - テスト容易性: OpenAI 呼び出し部分は差し替え可能（内部 _call_openai_api を patch）
    - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジームを判定
      - LLM 呼び出しは独立実装（news_nlp と private 関数を共有しない設計）
      - API エラー時はマクロセンチメントを 0.0 として継続（フェイルセーフ）
      - DuckDB を使ったデータ取得・計算と market_regime への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
      - しきい値に基づくラベル付与（bull / neutral / bear）
  - Data（ETL / カレンダー / パイプライン）
    - ETL パイプラインと結果型 (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
      - ETLResult データクラスを公開（フェッチ/保存件数、品質問題、エラー集約、has_errors 等のユーティリティ）
      - 差分更新・バックフィル・品質チェックを想定した設計（J-Quants クライアント連携想定）
    - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
      - market_calendar テーブルに基づく営業日判定およびユーティリティ関数群を提供
        - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
      - DB 未取得時は曜日（土日）ベースのフォールバックを利用して一貫性を保つ設計
      - calendar_update_job により J-Quants からの差分取得・バックフィル・健全性チェックを実行し保存
  - Research（因子計算・特徴量解析）
    - ファクター計算モジュール (src/kabusys/research/factor_research.py)
      - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER, ROE）を DuckDB SQL/ウィンドウ関数で実装
      - データ不足時の None 扱い、結果は (date, code) をキーとする dict のリストで返却
    - 特徴量探索 (src/kabusys/research/feature_exploration.py)
      - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を実装
      - pandas 等外部ライブラリに依存せず標準ライブラリ＋DuckDBでの実装
  - テスト性・堅牢性面の配慮
    - Look-ahead バイアス防止: 各モジュールで datetime.today()/date.today() の直接参照を避け、target_date を明示的引数として扱う
    - OpenAI 呼び出しやファイル読み込み失敗に対する明示的なフェイルセーフ（例: マクロスコア 0.0、スキップ、警告ログ）
    - DB 書込み時のトランザクション処理（COMMIT/ROLLBACK）、ROLLBACK 失敗時のログ

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / 設計上の重要なポイント
- 環境設定の自動読み込みはプロジェクトルート検出に依存するため、パッケージ配布後に意図せずファイル読み込みが行われるのを防ぐために KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。
- OpenAI API 呼び出しはレスポンスの形式（JSON mode）とエラー種別に応じた細かなリトライ/フォールバック処理を実装しており、運用中の不安定さを吸収する設計。
- DuckDB を中心に SQL ウィンドウ関数を活用して大規模銘柄群のファクター計算を効率的に実行する想定。
- DB 書込み処理は「部分成功時に既存データを過剰に消さない」戦略（対象コードを限定した DELETE → INSERT）をとっている。

今後の予定（メモ）
- strategy, execution, monitoring モジュールの実装およびエンドツーエンドの実運用テスト
- 詳細な品質チェックモジュール（data.quality）の追加と ETL ワークフローとの統合
- CI / テストケースの追加（OpenAI 呼び出しモック、DuckDB 上のユニットテストなど）