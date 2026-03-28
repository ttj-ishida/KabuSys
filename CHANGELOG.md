# Changelog

すべての重要な変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

- リリース方針: 主要バージョンは __version__ (src/kabusys/__init__.py) を参照してください。

## [Unreleased]

## [0.1.0] - 2026-03-28

初回公開リリース。日本株のデータプラットフォーム、リサーチ、AI スコアリング、環境設定ユーティリティを含む基本機能を実装しました。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化とバージョン管理を導入（__version__ = 0.1.0）。
  - サブパッケージ公開: data, strategy, execution, monitoring。

- 環境設定 / ロード
  - .env / .env.local ファイルと OS 環境変数を統合して設定を読み込む自動ローダ実装（src/kabusys/config.py）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト向け）。
    - .env パーサは export 形式、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
    - ファイル読み込み失敗時は警告を発生させてフォールバック。
  - Settings クラスで必要な設定をプロパティとして提供（J-Quants / kabuAPI / Slack / DB パス / 環境フラグ / ログレベル等）。
    - env 値や LOG_LEVEL の妥当性チェックを実装。
    - パス設定は Path.expanduser を使用。

- データ関連 (data)
  - ETL パイプライン基盤（src/kabusys/data/pipeline.py）
    - 差分取得、バックフィル、品質チェックの設計を反映した ETLResult データクラスを公開。
    - DuckDB のテーブル存在チェック、最大日付取得などのユーティリティを実装。
    - J-Quants クライアント経由での差分取得および idempotent 保存を想定。
  - calendar_management（市場カレンダー管理）
    - market_calendar を用いた営業日判定ロジックを実装。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
      - DB 登録値を優先し、未登録日は曜日ベースでフォールバックする一貫した挙動。
      - 最大探索日数の上限を設け無限ループを防止。
    - calendar_update_job により J-Quants からのカレンダー差分取得と冪等保存を実装（バックフィルと健全性チェック付き）。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して OpenAI (gpt-4o-mini) による銘柄単位センチメント評価を実装。
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換）を対象とする calc_news_window を提供。
    - バッチサイズ（最大 20 銘柄）、記事数や文字数上限のトリム、JSON mode の使用、レスポンス検証ロジックを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。失敗時はフェイルセーフでスキップ。
    - DuckDB の executemany の制約（空リスト不可）を回避する処理を実装。
    - API レスポンスの堅牢なパースとバリデーション（results 配列、コード照合、スコアの数値性、クリッピング ±1.0）。
    - score_news API: 成功した銘柄数を返す（書き込みは DELETE → INSERT の部分置換で冪等性を確保）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news / market_regime を参照し、ma200_ratio 計算、マクロ記事抽出、OpenAI 呼出し、スコア合成、冪等 DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - OpenAI 呼び出しは JSON レスポンスを期待し、失敗時は macro_sentiment=0.0 として継続するフェイルセーフを採用。
    - リトライ（最大 3 回）・指数バックオフ・5xx とそれ以外のハンドリングを実装。

- リサーチ（src/kabusys/research）
  - factor_research（ファクター計算）
    - calc_momentum: 約1ヶ月/3ヶ月/6ヶ月のリターン、200 日移動平均乖離 (ma200_dev) を計算。
    - calc_volatility: 20 日 ATR、ATR の相対指標、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER, ROE を計算（EPS が 0/欠損時は None）。
    - DuckDB を用いた SQL 実行と結果を dict リストで返す設計。
  - feature_exploration（特徴量探索・評価）
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）の将来リターンを一括で取得する効率的クエリを実装。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算するユーティリティ（有効レコードが 3 未満なら None）。
    - rank: 同順位は平均ランクとするランク変換実装（浮動小数の丸め対策あり）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算する統計サマリー機能。

- テストフレンドリー/安全設計
  - OpenAI 呼び出し箇所は内部で _call_openai_api を分離しており、ユニットテスト時にモック可能。
  - ルックアヘッドバイアス対策: datetime.today()/date.today() を直接参照しないスタイルで日時ウィンドウを計算する（target_date に厳密に依存）。
  - DuckDB の互換性考慮（executemany の空リスト回避など）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 注意事項 / 既知の設計決定
- OpenAI によるスコアリングは外部 API への依存があるため、API キー未設定時は ValueError を送出する仕様です（api_key 引数 or 環境変数 OPENAI_API_KEY）。
- API 不安定時はソフトフォールバック（スコア 0.0、または該当銘柄のスキップ）を行い、全体処理の停止を避けます。
- DuckDB を主要な永続層として想定しており、SQL ロジックはその特性（型や executemany の挙動）に合わせて調整済みです。
- 一部の処理はログ（INFO/WARNING/DEBUG）で詳細を出力します。運用時は LOG_LEVEL 設定で制御してください。

---

今後のリリースでは以下の改善を検討:
- strategy / execution / monitoring の具備（実装の拡張）。
- ai のモデル選択・並列化、バッチ処理の最適化。
- ETL の監視ダッシュボードや自動通知（Slack 連携など）。
- テストカバレッジの拡充と CI パイプライン整備。

（以上）