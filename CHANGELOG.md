# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このリポジトリの初期リリース情報を、コードベースから推測して記載しています。

全般
- バージョンはパッケージメタデータ (kabusys.__version__) により 0.1.0 としてリリースされています。

[0.1.0] - 2026-04-03
================================

Added
- パッケージ骨格
  - kabusys パッケージの公開モジュールとして data, strategy, execution, monitoring を定義。
  - バージョン情報を kabusys.__version__ = "0.1.0" として追加。

- 環境設定 / ロード機能 (kabusys.config)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロードの無効化をサポート。
  - .env パーサーは以下に対応：
    - export KEY=val 形式
    - シングル/ダブルクォート中のバックスラッシュエスケープ
    - クォートなしの場合のコメント (# 前の空白でコメント扱い)
  - .env の読み込みは OS 環境変数を保護する仕組み（protected set）を持つ（.env.local は上書き可能）。
  - Settings クラスを公開（settings インスタンス）。J-Quants / kabuステーション / LINE / DB / 監視 / システム設定等のプロパティを提供。
  - 環境変数検証（KABUSYS_ENV: development|paper_trading|live、LOG_LEVEL: DEBUG|INFO|...）を実装。
  - 必須変数未設定時は ValueError を送出する _require ユーティリティ。

- AI モジュール（kabusys.ai）
  - ニュースセンチメントスコアリング: score_news (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約して銘柄ごとの記事を作成。
    - OpenAI (gpt-4o-mini) の JSON Mode を用いたバッチ評価（最大 20 銘柄／チャンク）。
    - リトライ（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実施。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、code/score 検証、スコアの ±1.0 クリップ）。
    - 成功した銘柄のみ ai_scores テーブルに部分置換（DELETE → INSERT）して部分失敗時の既存データ保護。
    - calc_news_window: JST 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を UTC naive datetime に変換するユーティリティ。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。

  - 市場レジーム判定: score_regime (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を計算。
    - prices_daily からのデータ取得は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを防止。
    - マクロキーワードで raw_news のタイトルを抽出し OpenAI で JSON 形式の macro_sentiment を取得。
    - API エラー時は macro_sentiment を 0.0 とするフェイルセーフ（例外を上げずに継続）。
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時 ROLLBACK）。

- Data モジュール（kabusys.data）
  - ETL パイプライン結果の公開型 ETLResult を追加（kabusys.data.pipeline と kabusys.data.etl の再エクスポート）。
    - ETL 実行結果、取得/保存レコード数、品質チェック結果（quality_issues）、エラーリストを含む dataclass。
    - has_errors / has_quality_errors / to_dict のユーティリティを備える。
  - 市場カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を参照/更新するユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等的に更新（バックフィル・健全性チェックあり）。
    - DB 登録がない場合は曜日に基づくフォールバック（週末は非営業日）。
    - 最大探索日数の制限（無限ループ防止）や異常時の警告ログ実装。
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - 差分更新、保存（jquants_client 経由で idempotent 保存）、品質チェックのフロー設計に対応。
    - internal utilities: テーブル存在確認、最大日付取得など（DuckDB 前提）。

- Research モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev を prices_daily から計算。データ不足時は None を返す。
    - calc_volatility: atr_20、atr_pct、avg_turnover、volume_ratio を計算（ATR の NULL 伝播制御など）。
    - calc_value: raw_financials から最新財務を取得して PER, ROE を計算（EPS が 0/欠損なら None）。
    - 全関数は DuckDB を直接 SQL で活用し、外部 API に依存しない設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 将来リターン（指定ホライズン）を LEAD を使って一括で計算。horizons の検証あり。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。少ないデータや等分散時は None を返す。
    - rank: 同順位は平均ランクとなるランク化実装（丸め誤差対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- API キー/機密値は Settings 経由で環境変数から取得。必須キー未設定時に明示的なエラーを発生させることで誤動作を抑止。

Notes / 動作上の注意
- OpenAI 関連
  - 使用モデルは gpt-4o-mini、JSON Mode を利用して厳密な JSON を期待する設計。外部応答のノイズ対策（最外の {} を抽出する等）を実装。
  - OPENAI_API_KEY が未設定の場合、score_news と score_regime は ValueError を投げる。
  - API コールはテスト時に差し替え可能（内部の _call_openai_api をモック可）。

- DB 書き込み
  - ai_scores / market_regime 等への書き込みは部分失敗で既存データを不必要に消さないよう配慮（対象コードを絞って DELETE → INSERT）。
  - すべての重要な書き込みは BEGIN / COMMIT で囲み、例外時は ROLLBACK を試行する（ROLLBACK 失敗は警告ログ）。

- ルックアヘッドバイアス対策
  - 日次判定・スコアリング系は内部で datetime.today() / date.today() を参照せず、必ず target_date を引数で受け取る設計。

- .env パーサーの仕様
  - クォート内のエスケープ文字対応や export プレフィックス対応を実装。
  - override 挙動: .env は OS 環境変数未設定のキーのみ設定、.env.local は既存値を上書き（ただし OS 環境変数は保護）。

- テスト性
  - OpenAI 呼び出し箇所やファイルI/O部分はモック・差し替えがしやすいように関数境界で切り出している。

Breaking Changes
- なし（初期リリース）。

今後の TODO / 改善予定（コードから推測）
- PBR・配当利回りなどバリューファクターの拡張（calc_value の注記に記載あり）。
- calendar_update_job の J-Quants クライアント周りの堅牢化や詳細ログ強化。
- strategy / execution / monitoring モジュールの具現化（現状 __all__ に名前があるが実装ファイルは含まれていない模様）。
- DuckDB バインドの互換性（executemany の空リスト回避等）に関する追加テスト。

-----

この CHANGELOG はコードベースの静的解析から推測して作成しています。実際のコミット履歴やリリースノートと異なる可能性があります。必要であれば、各モジュールの公開 API（関数シグネチャ、期待するテーブルスキーマ等）に基づき、より詳細な変更点・補足を追記します。