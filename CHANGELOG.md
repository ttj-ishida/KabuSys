# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
このプロジェクトはセマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-03-31

Added
- 初回公開: KabuSys 日本株自動売買システムのコア機能群を実装・公開。
- パッケージ構成
  - パッケージトップ (src/kabusys/__init__.py) に version と主要サブパッケージを公開 (data, strategy, execution, monitoring)。
- 環境設定
  - robust な .env ローダーを実装 (src/kabusys/config.py)。
    - プロジェクトルートを .git または pyproject.toml から自動検出して .env/.env.local を読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応）。
    - export プレフィックス・クォート文字列・エスケープ・コメント処理に対応したパーサを実装。
    - OS 環境変数の保護（.env.local は上書き可能だが既存 OS 環境変数は保護）機能を実装。
    - Settings クラスでアプリ設定をプロパティ経由で取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）。env 値/ログレベルのバリデーションを含む。
- AI モジュール
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols から銘柄ごとに記事を集約して OpenAI（gpt-4o-mini、JSON mode）へバッチ送信してセンチメントスコアを生成。
    - JST 時間ウィンドウの計算（前日 15:00 JST ～ 当日 08:30 JST をUTCに変換）。
    - チャンク毎に最大銘柄数 (_BATCH_SIZE=20)、記事数制限・文字数トリムを実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフのリトライ、レスポンスバリデーション（JSON 抽出、results 配列・code/score 検証）、スコアの ±1.0 クリップ、DuckDB への冪等書き込み（DELETE→INSERT）を実装。
    - テスト用に OpenAI 呼び出し関数をモック差し替え可能（_call_openai_api）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - prices_daily からのルックアヘッド防止クエリ設計、マクロキーワードによる raw_news フィルタ、OpenAI 呼び出し（gpt-4o-mini）とリトライ/フェイルセーフ（API失敗時 macro_sentiment=0.0）を実装。
    - market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT + ROLLBACK ハンドリング）。
    - テスト容易性のため news_nlp とは別実装の _call_openai_api（モジュール結合を避ける設計）。
- Data モジュール
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar を用いた営業日判定ユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にカレンダーがある場合は DB 値優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - calendar_update_job により J-Quants API から差分取得・バックフィル・健全性チェックを行い market_calendar を冪等更新。
    - 最大探索日数やバックフィル期間など運用パラメータを定義し無限ループや誤登録を防止。
  - ETL / パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを公開（取得数・保存数・品質問題・エラーの集約）。
    - 差分取得、バックフィル、品質チェックの設計方針に基づくユーティリティ（_get_max_date 等）を実装。
    - jquants_client と quality モジュールを組み合わせて安全にデータ保存する設計。
- Research モジュール (src/kabusys/research/*)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Volatility（20日 ATR/相対ATR/平均売買代金/出来高比率）、Value（PER/ROE）等の定量ファクターを実装。
    - DuckDB の SQL ウィンドウ関数を利用し、データ不足時は None を返すなど堅牢に実装。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク関数（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部依存を持たない純 Python 実装で、ランクの同順位は平均ランクで処理。
- 監視・実行・戦略関連の初期インターフェースをパッケージ構成で用意（__all__ に strategy/execution/monitoring を含む）。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Notes / 設計上の注意
- ルックアヘッドバイアス防止: 多くのモジュール（news_nlp, regime_detector, research 等）は datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計です。
- OpenAI 呼び出しは gpt-4o-mini と JSON mode を用いる想定で実装。API キー未設定時は ValueError を送出する箇所があるため、運用時は環境変数 OPENAI_API_KEY の設定が必要です。
- API エラーやパースエラーは多くの箇所でフェイルセーフ（スコアに 0.0 を使う、処理スキップ）になっており、部分的な失敗時にも他データを保護する DB 書き込み戦略（コード絞り込みによる DELETE→INSERT 等）が採用されています。
- テスト容易性: OpenAI 呼び出し関数は各モジュール内で独自にラップしており、ユニットテストでモック差し替えが可能です。

今後の予定（想定）
- strategy / execution / monitoring の具体実装と統合テスト
- jquants_client の実装・運用検証、ETL のスケジューリングと監査ログ強化
- モデル・ファクターの検証（IC 分析を用いた改善）、および運用監視アラートの追加

--- 

追記: 本 CHANGELOG はソースコードから推測して作成しています。実際のリリースノートとして公開する場合は、実運用・変更履歴に合わせて調整してください。