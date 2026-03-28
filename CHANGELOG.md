# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

- リリース定義済み語彙: Added, Changed, Fixed, Removed, Security
- 日付表記は ISO 形式 (YYYY-MM-DD)

## [Unreleased]

## [0.1.0] - 2026-03-28
初回公開リリース。日本株自動売買プラットフォームのコア機能群を実装しました。
主に以下のサブシステムを含みます: 環境設定管理、データ ETL / カレンダー管理、機械学習補助（ニュース NLP / レジーム判定）、ファクター研究ユーティリティ。

### Added
- パッケージ公開情報
  - kabusys パッケージ初期バージョンを導入（src/kabusys/__init__.py）。
  - __version__ = "0.1.0"、トップレベル __all__ に data, strategy, execution, monitoring を公開。

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする機能を追加。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可。
  - .env パーサを実装（export プレフィックス、クォート、エスケープ、インラインコメントの取り扱いに対応）。
  - Settings クラスを導入し、J-Quants / kabuステーション / Slack / DB パス / 実行環境・ログレベルをプロパティ経由で取得。
  - 必須環境変数未設定時は明瞭な ValueError を送出する _require 機能。
  - 環境値検証: KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の検証。

- ニュース NLP（src/kabusys/ai/news_nlp.py / src/kabusys/ai/__init__.py）
  - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini、JSON Mode）で銘柄ごとにニュースセンチメントを算出し ai_scores テーブルへ書き込み（score_news）。
  - 時間ウィンドウ計算（前日 15:00 JST～当日 08:30 JST）を calc_news_window として提供。
  - バッチ処理（最大 20 銘柄 / API コール）、1 銘柄あたりの記事数・文字数制限（トークン肥大化対策）を実装。
  - エラー耐性：429・ネットワーク断・タイムアウト・5xx を指数バックオフでリトライ、API/パース失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
  - レスポンスバリデーション実装（JSON 抽出、results リスト検査、コード確認、数値チェック、スコア ±1.0 クリップ）。
  - テスト容易性のため OpenAI 呼び出しを内部関数でラップし、ユニットテスト時のモックを想定。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321 の 200 日移動平均乖離（重み70%）とニュース由来のマクロセンチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出し market_regime に保存（score_regime）。
  - マクロニュース抽出、LLM（gpt-4o-mini）でのセンチメント評価、リトライ・フォールバックロジックを実装。
  - API キー注入可能（引数または環境変数 OPENAI_API_KEY）。
  - ルックアヘッドバイアス防止: date < target_date の排他クエリを使用し、datetime.today() を参照しない設計。
  - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等性を確保し、失敗時に ROLLBACK を試行。

- データモジュール（src/kabusys/data/*）
  - ETL パイプラインインターフェース（pipeline.py / etl.py）を実装。
    - ETLResult データクラスを追加（取得/保存件数、品質問題、エラー集約、シリアライズ用 to_dict）。
    - 差分取得、バックフィル、品質チェックを想定した設計（J-Quants クライアント経由の保存処理を想定）。
  - マーケットカレンダー管理（calendar_management.py）
    - market_calendar テーブルに基づく営業日判定ユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データ優先だが未登録日は曜日ベース（週末）でフォールバックする一貫したロジック。
    - カレンダー差分取得・夜間更新ジョブ（calendar_update_job）を実装（J-Quants クライアント呼び出し想定・バックフィル・健全性チェックあり）。
    - 最大探索範囲やバックフィル日数などの安全パラメータを導入。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - calc_momentum, calc_value, calc_volatility を実装（prices_daily, raw_financials を使用）。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
    - Volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率。
    - Value: per（EPS が 0 または欠損なら None）、roe（直近報告ベース）。
  - 特徴量探索ユーティリティ（feature_exploration.py）
    - calc_forward_returns（複数ホライズンでの将来リターン算出）、horizon 検証。
    - calc_ic（Spearman ランク相関による IC 計算、最小サンプル数チェック）。
    - rank（同順位は平均ランクで処理、丸め誤差対策あり）。
    - factor_summary（count/mean/std/min/max/median の集計）。
  - zscore_normalize は kabusys.data.stats から再エクスポート（research パッケージの __init__ で公開）。

- 実装上の共通設計方針（ドキュメント付属）
  - ルックアヘッドバイアス防止の徹底（日時参照の排除、SQL の排他条件）。
  - DuckDB を使用したローカル分析基盤想定。
  - DB 書き込みは冪等性を意識（DELETE→INSERT、ON CONFLICT を期待）。
  - テスト容易性を考慮したモックポイント（OpenAI 呼び出しのラッピングなど）。
  - ロギングによる可観測性強化（info/warning/exception の適切な出力）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

---

注意事項 / 利用上のメモ
- 必要ランタイム依存: duckdb, openai 等のクライアントライブラリが想定されています（setup/requirements にて明示してください）。
- OpenAI API を利用する機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）を必要とします。テスト時は api_key 引数で注入するか、内部の呼び出しをモックしてください。
- .env の自動読み込みはプロジェクトルート探索を行います。配布後に CWD に依存せずに動作するよう設計されていますが、意図しない読み込みを避けるため KABUSYS_DISABLE_AUTO_ENV_LOAD を利用できます。
- DuckDB への executemany 呼び出しに対する互換性対策（空リストを与えないチェック）が一部に含まれます。DuckDB のバージョン差異に注意してください。

今後の予定（想定）
- strategy / execution / monitoring サブパッケージの具象実装（発注エンジン・監視/通知ロジックなど）の追加
- テスト・CI の整備、型チェック・静的解析ルールの導入
- ドキュメント（User Guide / Developer Guide）の充実

もし詳細な変更点をバージョン単位やモジュール単位でさらに分割したい場合は、どの粒度で記載するか指示してください。