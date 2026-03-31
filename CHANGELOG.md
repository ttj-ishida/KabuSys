CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは「Keep a Changelog」に準拠します。  
リリース日はリポジトリ内の __version__／現行日付に基づき設定しています。

Unreleased
----------
（なし）

[0.1.0] - 2026-03-31
--------------------
Added
- パッケージ初期リリース。
- 基本パッケージ情報
  - パッケージ名とバージョンを src/kabusys/__init__.py に追加（__version__ = "0.1.0"）。
  - public API の __all__ を定義（data, strategy, execution, monitoring）。
- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込みを実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
  - .env パーサーの実装。export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - .env 読み込み時に既存の OS 環境変数を保護する protected 機能と override オプション。
  - Settings クラスを提供し、アプリケーション設定をプロパティとして安全に取得可能に:
    - J-Quants / kabu ステーション API キーや Slack トークン、DB パス、監視しきい値、実行環境（development/paper_trading/live）、ログレベル検証などを含む。
  - 必須環境変数未設定時は明確な ValueError を発生させる _require 実装。
- AI モジュール（src/kabusys/ai/）
  - news_nlp（src/kabusys/ai/news_nlp.py）
    - raw_news テーブルを集約して OpenAI（gpt-4o-mini）へ送信し、銘柄別センチメント（ai_scores）を書き込む機能を実装。
    - 時間ウィンドウの計算 (前日15:00 JST ～ 当日08:30 JST を UTC に変換) を calc_news_window で提供。
    - バッチ処理（1コール最大20銘柄）、1銘柄あたりの最大記事数・文字数トリム、429/ネットワーク/タイムアウト/5xx に対する指数バックオフとリトライ。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、code/score 検証、スコアを ±1.0 にクリップ）。
    - DuckDB へは置換（DELETE → INSERT）で冪等的に書き込み。部分失敗時に他銘柄の既存スコアを保護する実装。
    - テスト用に OpenAI 呼び出し部分を差し替え可能（_call_openai_api を patch 可能）。
  - regime_detector（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して「market_regime」テーブルへ日次判定を行う機能を実装。
    - ma200_ratio 計算（target_date 未満のデータのみ使用しルックアヘッドを防止）、マクロキーワードで raw_news をフィルタして記事を取得、LLM（gpt-4o-mini）により macro_sentiment を算出。
    - API エラー時はフェイルセーフとして macro_sentiment=0.0 を使用。
    - レジームスコアの合成と閾値に基づくラベリング（bull / neutral / bear）。
    - market_regime への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とトランザクションロールバック処理。
    - OpenAI 呼び出しのリトライ処理（RateLimit / 接続エラー / タイムアウト / 5xx を考慮）。
- Data モジュール（src/kabusys/data/）
  - calendar_management（src/kabusys/data/calendar_management.py）
    - JPX カレンダー（market_calendar）管理機能を実装。is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを提供。
    - DB にカレンダー情報が存在する場合は DB 値を優先、未登録日や NULL は曜日ベースのフォールバック（週末判定）を行う設計。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）やカレンダー先読み・バックフィル・健全性チェックを備えた calendar_update_job 実装。J-Quants クライアント（jquants_client）経由で差分取得・保存を行う。
  - ETL / Pipeline（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult dataclass を導入し、ETL 実行結果（取得数・保存数・品質問題・エラー）を構造化して返却可能。
    - 差分更新、バックフィル、品質チェック（quality モジュール連携）を想定した ETL パイプライン設計（J-Quants API からの差分取得、idempotent 保存、品質チェックの収集）。
    - DuckDB に対する互換性考慮（executemany に空リストを渡さない等）。
    - etl.py から ETLResult を公開再エクスポート。
- Research モジュール（src/kabusys/research/）
  - factor_research（src/kabusys/research/factor_research.py）
    - モメンタム・ボラティリティ・バリュー系ファクター計算を実装:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ウィンドウ不足時は None）を算出。
      - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を算出。
      - calc_value: raw_financials から最新の財務情報を取得し PER / ROE を計算（EPS 欠損時は None）。
    - DuckDB を用いた SQL ベースの効率的な計算と結果を辞書リストで返す設計。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（Spearman ρ）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を追加。
    - pandas 等に依存せず、標準ライブラリ + DuckDB のみで集計する実装。
  - research パッケージ __init__ で主要関数を再エクスポート。
- 共通設計・品質
  - ルックアヘッドバイアス防止: 全ての分析/スコアリング関数は内部で datetime.today()/date.today() を直接参照せず、target_date を受け取る設計。
  - OpenAI 呼び出し部分は各モジュールで独立実装し、テスト時に差し替え可能にしてモジュール結合を低減。
  - トランザクション（BEGIN/COMMIT/ROLLBACK）を用いた冪等保存と失敗時のロールバック保護。
  - ロギングを各モジュールに導入し、処理の中間結果や警告（データ不足・API 異常など）を明示。

Changed
- 初回リリースのため変更履歴なし。

Fixed
- 初回リリースのため修正履歴なし。

Security
- 初回リリースのためセキュリティ告知なし。

Notes / 既知の設計意図
- OpenAI API キーは引数で注入可能（api_key）かつ環境変数 OPENAI_API_KEY の参照を行う。未設定時は明示的に ValueError を発生させる。
- news_nlp/regime_detector などでは LLM の失敗をフェイルセーフ（スコア 0.0）で扱い、上位プロセスが継続できるように設計している。
- DuckDB のバージョン差異（executemany の空リスト取り扱い等）に配慮した実装になっている。
- jquants_client や quality モジュール等の外部依存はインターフェース（import）を想定しており、実際の API 実装／テストダブルは外部で提供する必要がある。

Authors / Contributors
- コードベースから推測して作成（実際のコントリビュータはリポジトリのコミット履歴を参照してください）。

References
- 各モジュールの docstring と関数注釈に基づいて項目をまとめています。