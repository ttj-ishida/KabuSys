# Changelog

すべての注目すべき変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠します。  
安定したリリースについてはセマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主にデータ取得・ETL・マーケットカレンダー管理・ファクター計算・ニュースNLP・市場レジーム判定・環境設定を提供します。

### Added
- パッケージ基礎
  - kabusys パッケージのバージョン情報を追加（__version__ = "0.1.0"）。
  - 主要サブパッケージを公開: data, strategy, execution, monitoring を __all__ に含める。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml）を実装し、CWD に依存しない自動読み込みを実現。
  - .env パーサ（export 形式、クォート、エスケープ、インラインコメント対応）を実装。
  - 自動読み込みの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB パス / システム設定をプロパティで取得。環境変数の必須チェックを行う _require を提供。
  - KABUSYS_ENV, LOG_LEVEL 等の値検証（許容値チェック）を実装。

- データプラットフォーム (kabusys.data)
  - ETL インターフェースを公開（ETLResult の再エクスポート）。
  - ETL パイプライン基盤（kabusys.data.pipeline）を実装：
    - 差分取得・バックフィル・品質チェックを想定した ETLResult dataclass を実装。
    - DuckDB 上での最終取得日検出ユーティリティ、テーブル存在チェック等を実装。
  - マーケットカレンダー管理（kabusys.data.calendar_management）を実装：
    - market_calendar を使った営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録がない場合の曜日ベースフォールバック（週末除外）を提供。
    - JPX カレンダーの夜間差分更新ジョブ calendar_update_job を実装（J-Quants クライアント経由で差分取得・冪等保存、バックフィル、健全性チェック）。
  - ETL の設計方針・堅牢化（部分失敗保護、DuckDB executemany の空リスト回避など）をドキュメント化して実装。

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメントスコアリングを実装（score_news）。
  - JST ベースのニュース収集ウィンドウ計算（calc_news_window）を実装。ルックアヘッドを防ぐため datetime.today() を参照しない設計。
  - 1銘柄あたりのトークン肥大対策（記事数上限・文字数トリム）、バッチ処理（最大20銘柄/コール）をサポート。
  - OpenAI 呼び出しのリトライ（429・接続断・タイムアウト・5xx に対する指数バックオフ）とフェイルセーフ（失敗時はスキップ）を実装。
  - レスポンスのバリデーション（JSON の整形抽出、results 配列チェック、コード照合、スコア数値検証）を実装。スコアを ±1.0 にクリップ。
  - テスト容易性のため _call_openai_api を patch 可能にしている。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の market_regime を判定・保存する score_regime を実装。
  - マクロニュース抽出（キーワードベース）・LLM でのセンチメント評価（gpt-4o-mini）・リトライ/フェイルセーフを実装。
  - ma200_ratio の不足時の中立フォールバック（1.0）、API 失敗時の macro_sentiment=0.0 フォールバックを実装。
  - market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）および例外時の ROLLBACK 処理を実装。

- リサーチ / ファクター群（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER, ROE）を DuckDB 上の SQL で実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 返却等の安全設計。
  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）:
    - 将来リターン計算（calc_forward_returns、任意 horizon 対応、入力検証）。
    - IC（Information Coefficient: Spearman）計算（calc_ic）、およびランク変換ユーティリティ（rank）。
    - ファクター統計サマリー（factor_summary）。
  - research パッケージの __all__ を整備して主要関数を再エクスポート。

### Fixed
- DuckDB 関連の互換性問題を考慮
  - executemany に空リストを渡せない（DuckDB 0.10 の制約）問題への対応（空チェックを実装）。
- OpenAI 呼び出しのエラーハンドリング強化
  - APIError の status_code 存在有無に依存しない安全な分岐、5xx はリトライ対象とし、それ以外はスキップする扱いにした。

### Documentation / Design notes
- ルックアヘッドバイアス対策
  - 主要なスコア計算関数やウィンドウ計算は datetime.today()/date.today() を直接参照しない設計（target_date による決定）。
- ロギング
  - 各モジュールで詳細なログ出力（INFO / WARNING / DEBUG）を追加し、失敗時に挙動が追跡できるようにした。
- テスト容易性
  - 外部 API 呼び出し点（OpenAI クライアント呼び出し関数）は patch 可能な形で分離して実装。

### Known issues / Limitations
- OpenAI API キー（OPENAI_API_KEY）が未設定の場合、score_news / score_regime は ValueError を送出する（明示的な設定が必須）。
- 設定項目（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等）は環境変数または .env で提供する必要がある。
- 一部処理（jquants_client 呼び出し部分）は外部 API 実装に依存するため、ネットワークや API 仕様変更に影響される可能性がある。
- ai モジュールは LLM の出力フォーマットに依存しているため、モデル/モードの変更時にバリデーション調整が必要になる場合がある。

---

将来的リリースでは以下を検討しています:
- strategy / execution / monitoring の具体的な実装（現時点ではパッケージ名のみ公開）
- より詳細な品質チェックルール追加・自動モニタリング通知（Slack 連携の実装強化）
- OpenAI レスポンス形式やモデル変更に対応するための互換レイヤ追加

（補足）本 CHANGELOG はソースコードから推測して作成しています。実際のリリースノートやユーザー向けドキュメントは別途整備してください。