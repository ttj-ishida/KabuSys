# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用しています。

次のバージョンに関する未リリースの変更は Unreleased に記録します。

※ 注: 本 CHANGELOG はソースコードから推測して作成しています。実際のリリースノート作成時は差分・コミット履歴を参照してください。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買システム「KabuSys」のコアモジュール群を追加しました。設計方針として「ルックアヘッドバイアスの排除」「API 呼び出し失敗時のフェイルセーフ」「DuckDB 互換性への配慮」などが反映されています。

### Added
- パッケージの基本情報
  - パッケージ初期化: kabusys/__init__.py（__version__ = "0.1.0"、主要サブパッケージを __all__ に公開）。
- 設定管理
  - kabusys.config: 環境変数 / .env ファイルの読み込み機能を実装。
    - プロジェクトルート検出（.git または pyproject.toml による探索）に基づく自動 .env ロード。
    - .env のパース機能（export 形式、クォート・エスケープ対応、インラインコメント対応）。
    - .env の読み込み順序: OS 環境変数 > .env.local > .env（.env.local は override）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - Settings クラスに主要設定をプロパティとして提供（J‑Quants / kabu API / Slack / DB パス / 監視閾値 / 環境・ログレベル判定等）。
    - 設定値のバリデーション: 必須キー未設定時は ValueError、KABUSYS_ENV や LOG_LEVEL の許容値チェック。
- AI 関連
  - kabusys.ai.news_nlp: ニュース記事を集約して OpenAI（gpt-4o-mini）でセンチメントスコアを算出し、ai_scores テーブルへ書き込む処理を実装。
    - ニュース時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）。
    - 記事集約（銘柄ごとに最新 N 件、最大文字数でトリム）。
    - バッチ送信（最大 20 銘柄／チャンク）、JSON mode を利用した厳密な JSON 応答期待。
    - リトライ（429 / ネットワーク / タイムアウト / 5xx）と指数バックオフ、レスポンスのバリデーションとスコアクリップ（±1.0）。
    - DuckDB への冪等的書き込み（DELETE→INSERT）で部分失敗時の保護（書き込み対象を限定）。
    - テスト容易性のため _call_openai_api の差し替えが可能。
  - kabusys.ai.regime_detector: ETF (1321) の 200 日移動平均乖離とニュース由来のマクロセンチメントを合成して日次の市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ保存。
    - ma200_ratio の計算（target_date 未満のみ利用しルックアヘッドを防止）。
    - raw_news からマクロキーワードでフィルタしたタイトル取得。
    - OpenAI 呼び出し（gpt-4o-mini、JSON mode）、リトライとフェイルセーフ（API 失敗時は macro_sentiment=0.0）。
    - レジームスコア合成の重み付け（MA 70% / マクロ 30%）と閾値判定。
    - 冪等的 DB 書き込み（BEGIN / DELETE / INSERT / COMMIT、例外時は ROLLBACK）。
- データ基盤（Data）
  - kabusys.data.calendar_management: JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB データがない場合の曜日ベースフォールバック（週末を非営業日とする）、DB のまばらな登録への一貫した補完ロジック。
    - 夜間バッチ calendar_update_job（J‑Quants から差分取得 → 保存、バックフィル、健全性チェック）。
  - kabusys.data.pipeline / etl: ETL パイプライン用の基盤を実装。
    - ETLResult dataclass を公開（取得数、保存数、品質問題、エラー一覧などを保持）。
    - 差分取得・バックフィル・品質チェックの設計方針を反映。
  - kabusys.data.etl: pipeline.ETLResult の再エクスポート。
- Research
  - kabusys.research: ファクター計算・探索ユーティリティを公開。
  - kabusys.research.factor_research: モメンタム / ボラティリティ / バリュー系ファクターの計算関数を提供。
    - calc_momentum: 1M/3M/6M リターン・ma200 乖離の算出（不足時は None）。
    - calc_volatility: 20日 ATR, 相対 ATR, 20日平均売買代金, 出来高比率。
    - calc_value: raw_financials からの EPS/ROE を用いた PER/ROE 計算（最新財務レコードの取得）。
  - kabusys.research.feature_exploration: 将来リターン計算（複数ホライズン対応）、IC（Spearman）計算、ランク変換、ファクター統計サマリーなどを実装。
    - calc_forward_returns: 複数 horizon を同一クエリで取得、入力検証（horizons の範囲制約）。
    - calc_ic / rank / factor_summary を標準ライブラリのみで実装（pandas 非依存）。
- 公開 API の整理
  - 各パッケージで __all__ によるエクスポート整理（ai, research 等）。

### Fixed
- .env パースの堅牢化
  - クォート内のバックスラッシュエスケープ処理、export プレフィックス対応、インラインコメントの扱い（クォート有無による判定差）などの実装により、実用上の .env フォーマット差分に耐性を持たせました。
- OpenAI 呼び出しとレスポンス処理の耐障害性向上
  - JSON パース失敗時に最外の {} を抽出して復元するフェイルバック処理。
  - RateLimit / 接続エラー / タイムアウト / 5xx のリトライと適切なログ出力。
  - API エラーのステータスコード判定に安全な getattr を使用。
- DuckDB 互換性対応
  - executemany に空リストを渡すと失敗する DuckDB 0.10 の制約を回避するため、空チェックを行ってから executemany を呼ぶようにした。
- DB トランザクション安全性
  - INSERT 前に同日付・対象コードの DELETE を行い冪等性を担保。例外発生時の ROLLBACK 処理を追加・ログ出力を強化。

### Changed
- 設計方針（コード内ドキュメント）
  - 多くのモジュールで「datetime.today() / date.today() を直接参照しない」方針を採用し、関数引数で基準日を受け取る設計に統一。ルックアヘッドバイアスの排除を明示。
  - OpenAI 連携部分を各モジュールで独立実装し、モジュール間のプライベート関数共有を避けて差し替えテストを容易に。

### Security
- 現時点でセキュリティ修正の項目はありませんが、OpenAI API キー等の機密情報は Settings 経由で環境変数から取得する設計で、誤ってコードに埋め込まない方針を採用しています。

---

参考:
- Keep a Changelog: https://keepachangelog.com/ja/1.0.0/  
- Semantic Versioning: https://semver.org/