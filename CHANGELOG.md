# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠します。  
このプロジェクトはセマンティックバージョニングを採用します。

## [Unreleased]
- 今後のリリース向けの小さな改善や追加（未定）。

## [0.1.0] - 2026-03-28
初期リリース。日本株自動売買・データ基盤・リサーチ向けのコア機能を実装しました。以下はコードベースから推測できる主要な追加点と注意事項です。

### Added
- 基本パッケージ
  - kabusys パッケージの初期公開（__version__ = "0.1.0"）。
  - パッケージ構成例: data, strategy, execution, monitoring, research, ai, などのサブパッケージを公開。

- 設定・環境変数管理（kabusys.config）
  - .env 自動ロード機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - .env と .env.local の読み込み順序と上書きポリシー（OS 環境変数の保護機能）。
  - .env パースの強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のエスケープ処理
    - インラインコメントの扱い（クォートの有無に応じた切り分け）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト向け）。
  - Settings クラスによる型化されたアクセス（JQUANTS, kabu API, Slack, DB パス、環境種別、ログレベル等）。
  - env/log_level のバリデーション（許容値チェック）と便宜メソッド（is_live / is_paper / is_dev）。

- AI（自然言語処理）機能（kabusys.ai）
  - news_nlp.score_news:
    - raw_news と news_symbols を集約して銘柄ごとに記事をまとめ、OpenAI（gpt-4o-mini）でセンチメントを取得。
    - バッチ処理（最大バッチサイズ _BATCH_SIZE=20）、1銘柄あたり記事数/文字数上限を考慮したトリミング。
    - JSON Mode を利用したレスポンス検証と堅牢なパース（余分な前後テキストの復元も試行）。
    - レート制限・ネットワーク障害・5xx に対する指数バックオフリトライ、非リトライ対象の失敗はスキップ（フェイルセーフ）。
    - DuckDB に対して idempotent に書き換え（DELETE → INSERT）して部分失敗時のデータ保護。
    - calc_news_window による JST 基準のニュースウィンドウ計算（ルックアヘッドバイアス対策）。

  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ保存。
    - マクロニュースは news_nlp.calc_news_window を用いて収集、OpenAI 呼び出しは独自実装でモジュール結合を避ける設計。
    - API 障害時のフェイルセーフ（macro_sentiment = 0.0）、リトライ、レスポンスパース失敗時のログとフォールバック。
    - DB 更新はトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等性を確保。失敗時は ROLLBACK を試行。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率などを計算。true_range の NULL 伝播を適切に扱う。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS が不適切な場合は None）。
    - 設計方針: DuckDB + SQL を主体に、外部 API・発注ロジックへは一切アクセスしない安全な実装。

  - feature_exploration モジュール:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons のバリデーションあり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。データ不足時は None。
    - rank / factor_summary: ランク付けユーティリティ（同順位は平均ランク）、カラム別の統計サマリー（count/mean/std/min/max/median）。
    - zscore_normalize は data.stats から再エクスポート。

- データ基盤（kabusys.data）
  - calendar_management:
    - JPX カレンダー（market_calendar）を扱うユーティリティ群:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
      - calendar_update_job: J-Quants API からの差分取得と market_calendar への冪等保存（バックフィル・健全性チェック付き）
    - DB 登録がない/一部しかない場合の曜日ベースフォールバックロジックを一貫して提供。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）で無限ループを防止。

  - pipeline / etl:
    - ETLResult データクラスによる ETL 実行結果の集約（取得件数、保存件数、品質問題、エラーなど）。
    - 差分更新・バックフィル・品質チェック（quality モジュール呼び出しを想定）に基づく ETL 設計。
    - _get_max_date 等のユーティリティでテーブル未作成や空テーブルの扱いを考慮。

  - etl から ETLResult を再エクスポート。

### Changed
- （初期リリースのため該当なし）ただし設計上の決定点を明記:
  - すべての「日付参照」は datetime.today() / date.today() を直接参照しない設計（ルックアヘッドバイアス防止）。関数は target_date を明示的に受け取る。
  - DuckDB 0.10 の制約（executemany に空リスト不可）を考慮したコード実装。

### Fixed
- （初回リリースのため過去のバグ修正履歴はなし）
- ただし実装上の堅牢化:
  - .env の読み込み失敗時に warnings.warn を発行して処理継続。
  - OpenAI レスポンスパース失敗や API 障害に対してログを出しフォールバック（0.0 やスキップ）することで処理継続性を確保。

### Security
- .env 自動ロード時に既存 OS 環境変数を保護する仕組み（protected set）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD による自動環境読み込みの無効化でテストや CI での誤設定リスクを低減。
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY を想定。キー未設定時は ValueError を送出して明示的に失敗させる。

### Notes / Migration
- 初回利用時は .env を用意し、必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）を設定してください。Settings プロパティは未設定時に ValueError を投げます。
- OpenAI を用いる処理（score_news / score_regime）は API キーが必須です。テスト時は各モジュール内の _call_openai_api をモック可能です。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials, market_regime など）を事前に用意してください。ETL / calendar_update_job / pipeline はこれらのテーブルに依存します。

---

今後のリリースでは、次のような点が想定されます（未実装・改善候補）:
- strategy / execution / monitoring の具体的な取引実行フロー実装と安全ガードの追加。
- より豊富な品質チェックルールの実装（quality モジュールの拡張）。
- テストカバレッジの強化と CI ワークフローの公開。
- OpenAI モデルの選択肢拡張や並列リクエストの最適化。

（以上）