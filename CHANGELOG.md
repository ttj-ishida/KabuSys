# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

なお本ファイルは、提供されたソースコードから実装内容を推測して作成した初回リリース向けの変更履歴です。

## [Unreleased]

- ドキュメント／ユニットテスト向けの注記とモックポイントを追加（OpenAI呼出しの差し替え等）。
- 既知の制約・互換性注記を追記（DuckDB executemany の空リスト制約など）。

## [0.1.0] - 2026-03-27

初回公開リリース。本リポジトリの主要機能を実装。

### Added

- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージの公開モジュール一覧を __all__ で定義（data, strategy, execution, monitoring）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定値を自動ロードする機能を実装。
    - 自動ロードの優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env のパース実装: コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント扱いなどに対応。
  - 設定値アクセス用 Settings クラスを提供（J-Quants、kabuステーション、Slack、DBパス、環境名、ログレベル等）。
  - 必須環境変数未設定時は ValueError を送出する保護機能を提供。

- データプラットフォーム（kabusys.data）
  - calendar_management
    - 市場カレンダー管理機能を実装（market_calendar テーブル参照）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - DBデータ優先の判定、未登録日は曜日ベースでのフォールバックを提供。
    - calendar_update_job: J-Quants API から差分取得して冪等的に保存（バックフィル、健全性チェックあり）。
  - pipeline / etl
    - ETLResult データクラスを実装し ETL の実行結果を集約・シリアライズ可能に。
    - ETLパイプラインの補助ユーティリティ（テーブル存在確認、最大日付取得、トレーディング日調整ロジック等）を実装。
    - DuckDB を想定した互換性配慮（日付変換・executemany 空リスト回避等）。

- 研究（kabusys.research）
  - factor_research
    - ファクター計算: calc_momentum（1M/3M/6M、MA200乖離）、calc_volatility（ATR20、流動性指標）、calc_value（PER、ROE）を実装。
    - DuckDB を用いた SQL＋Python での実装。欠損・データ不足時の None 処理を明確化。
  - feature_exploration
    - 将来リターン計算: calc_forward_returns（複数ホライズン対応）。
    - IC（Information Coefficient）計算: calc_ic（スピアマンランク相関）。
    - ランク化ユーティリティ: rank（同順位は平均ランク）。
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）。
  - research パッケージのエクスポートを整備。

- AI（kabusys.ai）
  - news_nlp モジュール
    - score_news: raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）へバッチ問い合わせして銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書き込む。
    - チャンク処理（デフォルト 20 銘柄/チャンク）、1銘柄あたりの記事数・文字数制限（トリム）を実装。
    - JSON Mode（厳密な JSON 出力）を前提としたレスポンスバリデーションを実装。
    - リトライ（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実行。失敗時は個別チャンクをスキップしてフェイルセーフ。
    - DuckDB executemany の空リスト問題を回避する実装。
  - regime_detector モジュール
    - score_regime: ETF（1321）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して market_regime を日次で書き込む。
    - マクロニュース抽出（キーワードベース）、OpenAI 呼び出し（gpt-4o-mini）、スコア合成・ラベリング（bull/neutral/bear）を実装。
    - LLM呼出しは失敗時に macro_sentiment=0.0 にフォールバックするフェイルセーフ設計。
  - OpenAI クライアント呼び出しポイントはモジュール内で独立実装しており、ユニットテスト用に差し替え（mock）可能。

- 実装方針・品質設計
  - ルックアヘッドバイアス対策: 各モジュールは datetime.today() / date.today() を参照せず、呼び出し元が target_date を指定する設計。
  - DB 書き込みは冪等性を意識（BEGIN/DELETE/INSERT/COMMIT のパターン、ROLLBACK 保護）。
  - ロギングを広く配置し、警告・エラー時の動作が追跡可能。
  - DuckDB 互換性や将来の SDK 変更に備えた安全実装（例: APIError.status_code の getattr 利用など）。

### Changed

- 初版リリースにつき該当なし。

### Fixed

- 初版リリースにつき該当なし。

### Security

- APIキー（OPENAI_API_KEY 等）、Slack トークン、Kabu API パスワードなどは Settings 経由で必須チェックを行い、未設定の場合は ValueError を送出することで実行時の誤使用を防止。

### Notes / Known issues

- OpenAI SDK のバージョン差異に依存する部分（APIError の属性等）に対して互換性処理を入れているが、将来の SDK 変更で追加調整が必要になる可能性あり。
- DuckDB のバージョンによりプレースホルダや配列バインドの挙動が異なるため、executemany を利用する箇所では空リスト対策を行っている。将来的な DuckDB バージョンでの挙動変化に注意。
- news_nlp / regime_detector の OpenAI 呼び出しは外部 API に依存するため、レート制限や料金に注意して利用すること。
- calendar_update_job は J-Quants クライアント（jq.fetch_market_calendar / jq.save_market_calendar）実実装に依存する。API エラー時はログ出力の上で安全に 0 を返す。

---

作成・公開の目的やリリースポリシー（セマンティックバージョニングの運用等）は別途管理してください。必要であれば各モジュールごとの詳細な変更履歴（内部の関数単位や設計決定の理由）も生成できます。