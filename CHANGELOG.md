CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

バージョン管理規約: 0.y.z は初期・開発段階を示します。

Unreleased
----------

- 今のところ未リリースの変更はありません。

0.1.0 - 2026-04-02
------------------

初回リリース（コードベースの現時点スナップショット）。以下の主要機能と設計方針が実装されています。

Added
- 基本パッケージ定義
  - pakage __version__ を "0.1.0" に設定。トップレベルパッケージ kabusys の public モジュールを定義。

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動ロード機能（プロジェクトルートを .git または pyproject.toml から検出）。
  - export 形式・クォート・インラインコメント等に対応した堅牢な .env 行パーサー。
  - OS 環境変数の保護（protected set）と override 制御。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB / 監視 / ログ等の設定値をプロパティ経由で取得。
  - 環境変数の必須チェック（未設定時に ValueError を送出）と値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。

- AI 関連機能 (kabusys.ai)
  - ニュース NLU スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を元に、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）へ送信しセンチメントを算出。
    - JST 基準のニュース収集ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を calc_news_window で提供（UTC naive datetime を返す）。
    - バッチ処理（最大 20 銘柄/コール）、1銘柄当たり記事数/文字数上限（記事数:10、文字数:3000）。
    - JSON Mode を期待したレスポンスのバリデーションおよび復元処理（前後に余分なテキストが混入するケースを想定）。
    - スコアの ±1.0 クリッピング、バリデーション失敗時はスキップ・空辞書返却（フェイルセーフ）。
    - DuckDB への書き込みは idempotent（対象コードのみ DELETE → INSERT）で部分失敗時に他データを保護。
    - DuckDB 0.10 の制約（executemany に空リスト不可）への対応。
    - API 呼び出し失敗時のリトライ（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）とログ出力。
    - score_news: 書き込み件数を返す。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - prices_daily の過去データは target_date 未満の排他条件で取得し「ルックアヘッドバイアス」を防止。
    - マクロニュースは news_nlp 側で計算するウィンドウと整合。
    - OpenAI 呼び出しのリトライや API エラーの扱い、JSON パース失敗時のフェイルセーフ（macro_sentiment=0.0）。
    - DuckDB への書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等化。
    - 外部依存関数（OpenAI 呼び出し）はテストで差し替え可能な実装。

- データ基盤ユーティリティ (kabusys.data)
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を使った営業日判定とユーティリティ関数（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データが存在しない場合は曜日ベースのフォールバック（土日非営業）。
    - next/prev/get_trading_days は DB 値優先・未登録日は曜日フォールバックで一貫性を保持。
    - calendar_update_job: J-Quants から差分取得して market_calendar を idempotent に更新する夜間バッチ処理。バックフィル・健全性チェックを実装。

  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを提供（取得数・保存数・品質問題・エラー等を集約）。
    - 差分更新・バックフィル方針・品質チェックとの統合を想定した設計。
    - jquants_client と quality モジュールとの連携点を想定。

- リサーチ（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性指標（20 日平均売買代金・出来高比率）、バリューファクター（PER, ROE）を計算する関数を提供。
    - DuckDB SQL ベースで実装、結果を (date, code) をキーとした dict のリストで返す。
    - データ不足時の挙動（None を返す）を明示。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns、horizons の柔軟指定）。
    - IC（Information Coefficient）計算（スピアマンランク相関）、rank ユーティリティ（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）。
    - pandas 等に依存しない純標準ライブラリ実装。

- 共通設計・品質面の改善点
  - ルックアヘッドバイアス防止方針の徹底（datetime.today()/date.today() を分析ロジックで直接参照しない）。
  - DuckDB を想定した SQL 実装と互換性（空の executemany 回避など）。
  - OpenAI API 呼び出しでのリトライ・バックオフ、5xx と非5xx の分岐処理。
  - 例外を上位で扱う際のトランザクション安全性（ROLLBACK の失敗ログなどの安全ハンドリング）。
  - ロギングを適切に配置（INFO/DEBUG/WARNING/EXCEPTION）。

Changed
- （初回リリースのため該当なし）

Fixed / Improved
- DuckDB executemany の空パラメータ問題に対する対応を実装（空リスト時は実行をスキップ）。
- OpenAI API エラー処理: APIError の status_code 有無に依存しない安全な分岐を実装し、5xx はリトライ対象とする一方で非5xx は即時フェイル（フェイルセーフで macro_sentiment=0.0 等）に落とす挙動を明示。

Removed
- （初回リリースのため該当なし）

Security
- ユーザー提供の OpenAI API キーはパラメータ経由または環境変数 OPENAI_API_KEY で解決。未設定時は明示的な ValueError を送出して誤動作を防止。

Notes / Known limitations
- 実際の外部 API 呼び出し（OpenAI / J-Quants / kabu）はモックしやすいように実装が分離されていますが、本番運用では API レートや認証情報の取り扱いに注意が必要です。
- ai モジュールは JSON mode を期待するプロンプト設計ですが、LLM の挙動変化に対してレスポンス復元・バリデーションで対処する設計にしています。
- 一部の機能（例: PBR・配当利回りなどのバリュー指標）は現バージョンでは未実装（calc_value に注記あり）。

作者・貢献
- この CHANGELOG は提供されたコードベースから推測して作成しました。実際のリリースノート作成時は変更差分・コミット履歴・Issue 等を参照して更新してください。