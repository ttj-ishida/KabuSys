# Changelog

すべての注目すべき変更はこのファイルに記録します。  
形式は「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

現在のバージョン: `0.1.0`

## [Unreleased]

（次回リリースに向けた変更をここに記載します）

---

## [0.1.0] - 2026-03-28

初回公開リリース。日本株自動売買システム（KabuSys）の基盤機能をまとめて実装しました。主な追加点・設計上の方針・安全対策は以下の通りです。

### 追加 (Added)
- パッケージ基底
  - パッケージメタ情報を追加（src/kabusys/__init__.py、version `0.1.0`）。
  - パッケージ公開 API を `__all__` で整理（data, strategy, execution, monitoring）。

- 設定管理
  - 環境変数・設定読み込みモジュールを追加（src/kabusys/config.py）。
    - プロジェクトルート検出（.git または pyproject.toml を基準）により .env 自動読み込みを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロード無効化可能。
    - export プレフィックス対応、クォート文字列処理（バックスラッシュエスケープ考慮）、行内コメント処理など堅牢な .env パーサ実装。
    - 保護キー(_os_keys)により既存 OS 環境変数の上書きを防止可能。
    - Settings クラスを追加し、必要な設定値（J-Quants、kabu API、Slack、DB パス、環境種別、ログレベル等）をプロパティで提供。未設定時の明示的なエラーを発生させるユーティリティを用意。

- AI（NLP）モジュール
  - ニュースセンチメント解析（src/kabusys/ai/news_nlp.py）
    - OpenAI (gpt-4o-mini) を用いたニュースベースのセンチメントスコアリング。
    - タイムウィンドウ定義（前日 15:00 JST 〜 当日 08:30 JST）と window 計算ユーティリティ。
    - 銘柄ごとに記事を集約し、トークン肥大対策（最大記事数・最大文字数）でトリム。
    - バッチ処理（1コールあたり最大 20 銘柄）と JSON Mode 応答のバリデーション実装。
    - 再試行（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで行い、失敗時は安全にスキップして他銘柄処理を継続。
    - DuckDB への冪等書き込み（DELETE → INSERT）と、部分失敗時に既存データを保護する手法を導入。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返却。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードによる raw_news フィルタ、OpenAI 呼び出し（json 出力）とレスポンスパース、クリッピング処理を実装。
    - API エラーやパース失敗時はフェイルセーフとして macro_sentiment = 0.0 を使用。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とエラーハンドリング（ROLLBACK ロギング）を実装。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返却。

- データ（Data Platform）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - DB の有無や部分的な登録に対応する「DB 値優先、未登録は曜日フォールバック」の一貫した挙動。
    - 最大探索範囲を設定し無限ループを防止。
    - 夜間バッチ更新 job（calendar_update_job）で J-Quants から差分取得 → 保存（ON CONFLICT DO UPDATE）を実装。バックフィルと健全性チェックを導入。
  - ETL パイプラインインターフェース（src/kabusys/data/pipeline.py / etl.py）
    - ETL の結果を表現するデータクラス ETLResult を実装（取得件数、保存件数、品質チェック結果、エラー一覧等を含む）。
    - ETL モジュールでは差分更新、保存、品質チェックの設計方針を盛り込んだ基礎を追加（jquants_client / quality モジュール経由での処理を想定）。

- リサーチ（Research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M、ma200乖離）、Volatility（20日 ATR、相対ATR、出来高・出来高比等）、Value（PER、ROE）の計算関数を実装。
    - DuckDB のウィンドウ関数を活用し、データ不足時は None を返す設計。
    - 結果は (date, code) 単位の dict リストで返却。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns: 任意ホライズン対応、ホライズンのバリデーション、単一クエリで取得）。
    - IC（Information Coefficient）計算（スピアマンのランク相関）と rank ユーティリティ（同順位は平均ランク）。
    - ファクター統計サマリー（count/mean/std/min/max/median）を提供。
  - research パッケージの公開 API を整理（calc_momentum, calc_volatility, calc_value, zscore_normalize 等を再エクスポート）。

### 変更 (Changed)
- 設計方針の明確化・安全対策（全体）
  - ルックアヘッドバイアス対策として主要な処理（score_news, score_regime, 各ファクター計算）は内部で datetime.today()/date.today() を直接参照しない実装。
  - DuckDB を前提とした SQL と Python の組み合わせでパフォーマンスと可読性を両立する実装を採用。
  - 外部 API 呼び出し部分（OpenAI / J-Quants など）については呼び出し失敗時のフォールバックを徹底（例: macro_sentiment=0.0、個別チャンク失敗時はスキップ）。

### 修正 (Fixed)
- .env パーサの改善
  - export プレフィックス、シングル/ダブルクォート付き値のバックスラッシュエスケープ、行内コメントの扱いなど、実運用で問題になりがちなパターンに対応。

### セキュリティ（Security）/ 安全策
- 環境変数読み込み時に OS 環境変数を保護するため protected キーセットを導入。意図しない上書きを防止。
- OpenAI API キーは引数から注入可能（テスト容易性）かつ、引数が None の場合は環境変数 OPENAI_API_KEY を参照。未設定時は明確な ValueError を発生させる。

### 既知の制限 (Known issues / Limitations)
- 一部モジュールや関数は「骨格」実装（ETL の一部ヘルパ関数など）であり、外部クライアント（jquants_client や quality）や DB スキーマが前提となるため、これらの実体が必要。
- news_nlp / regime_detector などは OpenAI のレスポンス形式に依存しており、モデルや SDK の将来的変更に伴い微調整が必要になる可能性がある（status_code の取り扱い等は互換性対策あり）。
- 現リリースでは一部ファクター（PBR、配当利回り等）は未実装。

### 破壊的変更 (Breaking Changes)
- 初回リリースのため該当なし。

---

貢献・改良の提案、バグ報告、API 仕様の変更希望等は Issue を立ててください。