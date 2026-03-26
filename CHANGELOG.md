# Keep a Changelog — CHANGELOG.md（日本語）

すべての変更はセマンティックバージョニングに従います。  
このファイルは Keep a Changelog の形式に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-26
初期リリース。日本株自動売買システム「KabuSys」のコア機能群を実装・公開。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョンを src/kabusys/__init__.py で "0.1.0" として設定。
  - モジュール公開: data, strategy, execution, monitoring を __all__ で公開。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定をロードする自動ローダーを実装。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索。
    - 環境変数ロード順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサーの実装:
    - export KEY=val 形式の対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い、無効行スキップ等をサポート。
    - 上書き制御（override）と保護キーセット（protected）により OS 環境変数保護を実現。
  - Settings クラスを提供（settings インスタンスを公開）。J-Quants / kabuステーション / Slack / DB パス / システム設定（env, log_level, is_live 等）をプロパティ経由で取得。環境変数のバリデーション（有効値チェック）を実装。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）へバッチで投げてセンチメントスコアを生成。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC への変換を実装）。
    - チャンク処理（最大20銘柄/チャンク）、1銘柄あたりの記事数／文字数上限、JSON mode 応答パース、結果検証、スコア ±1.0 クリッピング、DuckDB への冪等書き込み（DELETE→INSERT）を実装。
    - API エラー（429・ネットワーク断・タイムアウト・5xx）は指数バックオフでリトライ、非リトライエラーはスキップして処理継続（フェイルセーフ）。
    - 公開関数: score_news(conn, target_date, api_key=None)
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を組み合わせて日次で市場レジームを判定（'bull' / 'neutral' / 'bear'）。
    - prices_daily / raw_news を参照してスコアを算出し、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI 呼び出しは専用実装、API の再試行・エラー処理とフェイルセーフ（API失敗時 macro_sentiment=0.0）を実装。
    - 公開関数: score_regime(conn, target_date, api_key=None)

- データ／ETL／カレンダー（kabusys.data）
  - calendar_management
    - JPX カレンダー管理: market_calendar テーブルに基づく営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB 登録値を優先し、未登録日は曜日ベースでフォールバック。最大探索日数制限で無限ループ防止。
    - 夜間バッチ更新 job（calendar_update_job）を実装。J-Quants から差分取得して保存、バックフィルと健全性チェックを実施。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを実装して ETL の取得数／保存数／品質問題／エラーを集約。
    - 差分更新、バックフィル、品質チェック（kabusys.data.quality へ委譲）を想定した設計。
    - jquants_client を用いた取得/保存の再利用を前提。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）。データ不足時の None 処理。
    - Volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率。
    - Value: PER, ROE（raw_financials からの最新財務データ参照）。PBR・配当利回りは未実装。
    - いずれも DuckDB 上で SQL を併用して計算。外部 API にアクセスしない設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: target_date から LEAD を使って任意ホライズンの将来終値リターンを計算（horizons の検証あり）。
    - IC（Information Coefficient）計算（calc_ic）: Spearman（ランク相関）を独自実装。十分な有効レコードがない場合は None を返す。
    - ランク関数（rank）: 同順位の平均ランク処理、丸めによる ties 対策。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。

### Changed
- （初期リリースのため該当なし）

### Fixed / Hardening
- 環境変数ローダーの堅牢化
  - .env 読み込み失敗時に警告を出し続行（読み込み例外を抑える）。
  - protected セットにより OS 環境変数の上書き防止。
- OpenAI API 呼び出し／レスポンス処理の堅牢化
  - 429 / ネットワーク / タイムアウト / 5xx を対象に指数バックオフとリトライを実装（news_nlp と regime_detector 共に）。
  - JSON パース失敗時の救済処理（文字列から最外の {} を抽出して再パース）を追加。
  - 不正応答時は例外を投げず該当チャンク/項目をスキップし、全体処理は継続（フェイルセーフ）。
  - スコアの数値検証と ±1.0 のクリップを実装。
- DB 書き込みの冪等性とトランザクション管理
  - market_regime / ai_scores への書き込みは BEGIN/DELETE/INSERT/COMMIT または executemany を用いた個別 DELETE → INSERT の形で冪等性を確保。
  - 失敗時は ROLLBACK を試行し、ROLLBACK 失敗時には警告ログを出力して例外を再送出。
  - DuckDB の executemany に対する空リスト制約回避（空の場合は実行しない）。
- ルックアヘッドバイアス防止
  - date.today() / datetime.today() をコアロジックで直接参照しない設計（target_date を明示引数として受ける）。
  - prices_daily クエリやニュースウィンドウは target_date 未満／特定ウィンドウの半開区間を用いる。
- calendar_management の堅牢性
  - market_calendar 未取得時のフォールバック（一貫した曜日ベース判定）。
  - 最終取得日の異常（将来日付が極端に遠い）を検知してジョブを安全にスキップ。

### Security
- 必須の機密情報（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）を Settings で厳密に要求し、未設定時は ValueError を発生させることで運用ミスを低減。

### Breaking Changes
- （初期リリースのため該当なし）

---

注意事項・運用メモ:
- OpenAI API の利用には環境変数 OPENAI_API_KEY の設定が必要です（各公開 API は api_key 引数を受け取るため、テストでは注入可能）。
- DuckDB に格納される日付は想定どおり date/UTC naive を扱うため、外部システムと連携する際は時刻基準の差に注意してください。
- .env 自動ロードはプロジェクトルート検出に依存します。パッケージ配布後やテスト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効にできます。

（以上）