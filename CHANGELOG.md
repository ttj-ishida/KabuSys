CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に従い、セマンティックバージョニングを採用しています。
（https://keep-a-changelog.com/ja/、https://semver.org/lang/ja/ を参照）

0.1.0 - 2026-04-01
------------------

Added
- 初版リリース。KabuSys パッケージの基本機能を実装。
- パッケージ公開情報
  - バージョン: 0.1.0
  - パッケージ説明: 日本株自動売買システム (kabusys)

- 環境設定管理 (kabusys.config)
  - .env / .env.local ファイルおよび OS 環境変数から設定を安全に読み込む自動ローダーを実装。
  - プロジェクトルートを .git または pyproject.toml を基準に検出するため、カレントワーキングディレクトリに依存しない設計。
  - .env パーサー:
    - export PREFIX=VALUE 形式やクォート／エスケープ、行末コメントの取り扱いに対応。
    - override フラグと protected キーセットで OS 環境変数の保護が可能。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をサポート（テスト時などに使用）。
  - Settings クラスを提供。J-Quants、kabuステーション API、Slack、データベースパス（DuckDB / SQLite）、監視 PID・閾値、実行環境（development/paper_trading/live）・ログレベルのバリデーション等をプロパティとして取得可能。
  - 必須環境変数未設定時は明示的に ValueError を送出。

- AI モジュール (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約して銘柄ごとのテキストを作成し、OpenAI (gpt-4o-mini) を用いて -1.0〜1.0 のセンチメントスコアを算出する score_news を提供。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB と比較）での記事を対象。
    - バッチ処理（最大 20 銘柄／回）、1 銘柄あたり記事件数・文字数のトリム制限を実装。
    - レスポンスの JSON バリデーション、既知でないコードの無視、スコアの ±1.0 へのクリップを実施。
    - API エラー（429、ネットワーク、タイムアウト、5xx）に対する指数バックオフのリトライ実装。致命的でない失敗はスキップして処理継続（フェイルセーフ）。
    - DuckDB の executemany の制約に配慮したトランザクション（DELETE → INSERT）で ai_scores へ書き込みを行う。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を提供。
    - ma200_ratio の計算は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを回避。
    - マクロニュース抽出はキーワードマッチ（複数キーワード）で行ない、記事がない場合は LLM 呼び出しをスキップして macro_sentiment=0 とするフェイルセーフ。
    - OpenAI 呼び出しは内部でリトライを行い、最終的に失敗した場合は macro_sentiment=0 を採用。
    - market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み。

- 研究用モジュール (kabusys.research)
  - factor_research
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER、ROE）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金、出来高比率）を DuckDB の prices_daily / raw_financials から計算する関数群 calc_momentum、calc_value、calc_volatility を実装。
    - データ不足時の None 戻り、ログ出力、営業日ベース（連続レコード数）でのホライズン計算等、実務的な考慮を含む。
  - feature_exploration
    - 将来リターン計算 calc_forward_returns（horizons のバリデーション、1 クエリでまとめて取得）、IC（Information Coefficient）計算 calc_ic（Spearman ランク相関）、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を提供。
    - pandas 等の外部ライブラリに依存せず、標準ライブラリ + duckdb で実装。

- データ基盤モジュール (kabusys.data)
  - カレンダー管理 (calendar_management)
    - market_calendar を用いた営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にカレンダーがない場合は曜日ベースのフォールバック（週末を非営業日）を採用し、DB がまばらでも一貫した判定結果を返すよう設計。
    - JPX カレンダー差分取得と夜間バッチ更新（calendar_update_job）を実装。バックフィル・健全性チェック（未来日付の異常検出）を備える。
  - ETL パイプライン (pipeline / etl)
    - ETLResult データクラスを公開。ETL 実行の取得件数／保存件数／品質チェック結果／エラーの集約を行う。
    - 差分更新、backfill による後出し修正吸収、品質チェックの収集（重大度により has_quality_errors で判定）が設計に含まれる。
    - jquants_client を介した idempotent な保存（ON CONFLICT 相当）と品質チェックモジュール連携を想定。

Other notable design decisions
- ルックアヘッドバイアス対策: 日次判定ロジックやニュースウィンドウ、ファクター算出は datetime.today()/date.today() を内部で参照しない設計（target_date 引数駆動）。
- フェイルセーフ設計: 外部 API の不安定さを考慮し、API 失敗時には処理をスキップまたはデフォルト値（例: macro_sentiment=0）で継続する実装が多く適用されている。
- DuckDB 互換性配慮: executemany の空リスト禁止等、DuckDB の挙動に対するワークアラウンドを多数実装。
- OpenAI 呼び出し: JSON Mode を想定したレスポンスパースロジックと、429/ネットワーク/タイムアウト/5xx に対するリトライ戦略を共通方針としている。

Fixed
- なし（初回リリース）

Changed
- なし（初回リリース）

Deprecated
- なし

Removed
- なし

Security
- API キーは環境変数経由で注入する設計（OPENAI_API_KEY 等）。鍵のハードコーディングは行っていない。
- .env 自動ロードは必要に応じて無効化可能（テスト用途）。

既知の制約 / 注意事項
- OpenAI 連携は gpt-4o-mini と JSON Mode を前提にしているため、将来のモデルや SDK 変更により微調整が必要になる可能性がある。
- DuckDB のバージョン差異（配列バインドや executemany の挙動）に起因する互換性問題が発生する可能性があるため、本番環境の DuckDB バージョンでの検証を推奨。
- ETL / pipeline の外部依存（jquants_client、quality モジュール等）は本リリース内での契約インターフェースに基づく実装を想定。実際の API の変更時にはアダプタ実装が必要になる場合がある。

Contributing
- バグ修正、テスト追加、機能改善は PR を歓迎します。ローカルでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境変数自動ロードを抑制できます。

--- 

（注）本 CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のリリース履歴やバージョン日付はプロジェクトの運用方針に従って調整してください。