# CHANGELOG

すべての重要な変更をここに記録します。本ファイルは Keep a Changelog の形式に準拠します。

フォーマット:
- 変更はバージョンごとにまとめ、カテゴリ（Added / Changed / Fixed / Deprecated / Removed / Security）で整理しています。

## [0.1.0] - 2026-03-28

### Added
- パッケージ初期リリースを追加（kabusys v0.1.0）。
  - パッケージトップ: src/kabusys/__init__.py にバージョン定義と主要サブパッケージの公開を追加（data, strategy, execution, monitoring）。

- 環境設定管理モジュールを追加（src/kabusys/config.py）。
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を使った自動ロード無効化に対応（テスト用）。
  - .env パーサーは以下をサポート:
    - コメント行、export プレフィックス、クォート付き／クォート無しの値、バックスラッシュエスケープ、インラインコメントの扱いの改善。
  - .env.local は .env より優先して上書き（ただし既存 OS 環境変数は保護）。
  - Settings クラスを提供し、アプリで使用する設定値をプロパティとして公開:
    - J-Quants / kabuステーション / Slack / データベースパス（DuckDB/SQLite）/ システム環境（KABUSYS_ENV）/ログレベル等。
  - env 値・LOG_LEVEL 値のバリデーションを実装（許容値外は ValueError を送出）。
  - 必須値未設定時に明確なエラーメッセージを返す _require 関数を実装。

- AI 関連モジュールを追加（src/kabusys/ai）。
  - news_nlp（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成する calc_news_window / _fetch_articles を実装。
    - OpenAI（gpt-4o-mini）を用いたバッチセンチメント評価機能 score_news を実装。
      - 1チャンク最大20銘柄（_BATCH_SIZE）、1銘柄あたり記事数上限・文字数トリムによるトークン制御を実装。
      - JSON Mode を利用した厳密なレスポンス検証とパース復元処理（前後余計なテキストが混入した場合の最外層 {} 抽出）。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ（リトライ）を実装。非再試行エラーはスキップして継続するフェイルセーフ動作。
      - スコアの ±1.0 クリッピング、部分失敗時に既存スコアを保護するための部分的な DELETE→INSERT ロジック（DuckDB の executemany の互換性に配慮）。
      - API キー注入（api_key 引数 or 環境変数 OPENAI_API_KEY）に対応。未設定時は ValueError を送出。
      - ログ出力（処理状況・失敗理由・書込み件数）を追加。
  - regime_detector（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の200日移動平均乖離（重み70%）と、マクロ経済ニュースの LLM センチメント（重み30%）を合成して日次市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - prices_daily からの ma200_ratio 計算（ルックアヘッド防止のため target_date 未満データのみ使用）と、raw_news からマクロキーワードでのフィルタ取得を実装。
    - OpenAI 呼び出し（gpt-4o-mini）と JSON パース、リトライ／フォールバック（API 失敗時は macro_sentiment=0.0）を実装。
    - 判定結果を market_regime テーブルへ冪等に書き込む（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試行。

- Research（研究）モジュールを追加（src/kabusys/research）。
  - factor_research（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）等のファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上で完結する SQL 中心の実装。データ不足時は None を返す仕様。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応、horizons 引数）、IC（Information Coefficient）計算 calc_ic（スピアマンランク相関）、rank（同順位は平均ランク処理）、統計サマリー factor_summary を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
  - research パッケージは data.stats の zscore_normalize を再エクスポート。

- データプラットフォーム関連モジュールを追加（src/kabusys/data）。
  - calendar_management（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日判定ユーティリティを実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - market_calendar 未登録時の曜日ベースフォールバックを用意（安全に一貫した振る舞い）。
    - 夜間バッチ calendar_update_job を実装（J-Quants API との差分取得／バックフィル／健全性チェックを含む）。J-Quants クライアントは jquants_client を利用。
    - 最大探索日数やバックフィル日数、先読み日数、健全性上限等の設定定数を導入。
  - pipeline / etl（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）
    - ETLResult データクラスを追加（ETL の取得・保存件数、品質チェック結果、エラーの集約）。
    - ETL パイプラインのユーティリティ関数群の骨格（差分取得、保存、品質チェック連携）を実装（jquants_client / quality モジュールとの協調を想定）。
    - data.etl は pipeline.ETLResult を再エクスポート。

- 内部ユーティリティ・堅牢性向上
  - DuckDB 結果からの日付変換、テーブル存在チェック、executemany の空パラメータ回避など、DB 周りの互換性と安全性を考慮したユーティリティを多数実装。
  - OpenAI 呼び出し箇所はテストで差し替え可能な内部 _call_openai_api を各モジュール内で定義（モジュール間でプライベート関数を共有しない設計）。

### Changed
- （初回リリース）該当なし。

### Fixed
- （初回リリース）該当なし。

### Deprecated
- （初回リリース）該当なし。

### Removed
- （初回リリース）該当なし。

### Security
- OpenAI API キーは引数で注入可能かつ環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出して安全性を確保。
- .env ファイル読み込みで既存 OS 環境変数を上書きしないよう保護（protected keys）を実装。

### Notes / 設計上の重要事項
- AI モジュール（news_nlp, regime_detector）やファクター計算は「ルックアヘッドバイアス防止」のため、内部で datetime.today()/date.today() を参照せず、必ず caller が target_date を渡す設計になっています。
- OpenAI 呼び出しは JSON Mode を前提に厳密な検証とフォールバックを行い、API の一時エラーやサーバーエラーに対してリトライとフェイルセーフ（スコア=0 またはスキップ）を行います。
- DuckDB との相互作用において、executemany に空リストを渡せない制約等への互換性配慮を行っています。
- strategy / execution / monitoring パッケージは __all__ に含まれているが、本リリースでの未実装・未公開の部分がある可能性があります（将来拡張予定）。

---

今後のリリースでは、以下を検討しています:
- strategy / execution / monitoring の実装と E2E の取引フロー（発注・ポジション管理）。
- テストカバレッジの充実と CI 統合。
- J-Quants / kabu API クライアントの詳細実装・認証フローの整備。