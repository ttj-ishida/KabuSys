CHANGELOG
=========

この変更履歴は「Keep a Changelog」の形式に準拠しています。  
セマンティックバージョニング (SemVer) を採用しています。

Unreleased
----------

- （今後の変更を記載）

[0.1.0] - 2026-04-04
--------------------

Added
- パッケージ基盤
  - kabusys パッケージの初期公開。バージョンは 0.1.0。
  - パッケージの公開インターフェースとして data, strategy, execution, monitoring を __all__ に設定。

- 環境設定 / 設定管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env ファイルパーサを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメントの取り扱い等に対応）。
  - 自動ロードを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを実装し、J-Quants / kabu API / LINE / DB パス / 監視パラメータ / ログレベルなど多くの設定プロパティを提供。
  - 設定のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）や必須環境変数取得時の明示的エラーを実装。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を用いて銘柄ごとのニュース集合を作成し、OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄別センチメント（-1.0〜1.0）を算出。
    - 前日 15:00 JST 〜 当日 08:30 JST のニュースウィンドウ計算ユーティリティ（calc_news_window）を実装。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/回）、1銘柄あたり記事上限・文字数上限によるトリミング、レスポンスのバリデーションとスコアクリッピングを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ処理を実装し、API障害時はフェイルセーフでスキップ（例外を投げず継続）。
    - DuckDB への書き込みは部分失敗に強い（対象コードのみ DELETE → INSERT）方式。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（Nikkei 225 連動型）について 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - LLM には gpt-4o-mini を使用。レスポンス失敗時は macro_sentiment = 0.0 として続行（フェイルセーフ）。
    - DuckDB の prices_daily/raw_news/market_regime を参照し、計算結果は冪等に market_regime テーブルへ保存（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK を試行）。
    - ルックアヘッドバイアス防止の設計（target_date 未満のデータのみ使用、datetime.today()/date.today() を内部で参照しない）。

- データプラットフォーム / ETL (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを用いた営業日判定ユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データがない/未登録日の場合は曜日ベースでフォールバック（週末は非営業日）。
    - 夜間バッチ calendar_update_job を実装し、J-Quants クライアントから差分取得→冪等保存（バックフィル、先読み、健全性チェック対応）。
    - 探索上限日数を設定して無限ループを防止。

  - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを提供し、ETL の取得件数／保存件数／品質問題／エラーを集約可能。
    - ETL 実装方針を反映（差分更新、バックフィル、品質チェックの収集方針、DuckDB 互換性への配慮）。
    - kabusys.data.etl で ETLResult を再エクスポート。

- リサーチ / ファクター計算 (kabusys.research)
  - ファクター計算群を実装（kabusys.research.factor_research）
    - Momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None を返す）。
    - Volatility/Liquidity: 20日 ATR（true range の NULL 伝播を考慮）、相対 ATR、20日平均売買代金、出来高比率。
    - Value: raw_financials から直近財務データを取得して PER / ROE を計算（EPS が 0/NULL の場合 PER は None）。
    - DuckDB 上の SQL+ウィンドウ関数を主体に実装し、外部 API へはアクセスしない設計。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応、入力検証付き）。
    - IC（Information Coefficient）計算（スピアマンのランク相関）、ランク化ユーティリティ（rank）。
    - ファクター統計サマリー（count/mean/std/min/max/median）を提供。
    - pandas 等に依存せず標準ライブラリのみで実装。

Other notable implementations / design choices
- DuckDB のバージョン差分に配慮した互換性実装（executemany の空リスト回避、LIST型バインドの不安定さへのワークアラウンド等）。
- OpenAI 呼び出しは各モジュール内で独立実装（モジュール間でプライベート関数を共有しない）、テスト時に差し替え可能（unittest.mock.patch を想定）。
- ルックアヘッドバイアス回避を各種モジュール設計で徹底（target_date 未満のデータ利用、date.today() の未使用）。
- ロギングとフェイルセーフを重視。API エラーやパースエラー時は警告ログを出し、可能な限り処理継続。

Fixed
- 初版リリースのため該当なし。

Security
- 初版リリースのため該当なし。
  - 注意: OpenAI API キー等の機密情報は環境変数で管理する想定（Settings._require により未設定時は明示エラー）。

Known limitations / Notes
- strategy、execution、monitoring パッケージの内部実装は本リリースのスコープに含まれていない（__all__ に名前のみ存在）。
- OpenAI を用いるモジュールは外部 API に依存しており、API 仕様／SDK バージョンの変化で挙動が変わる可能性がある（API エラー処理は盛り込まれているが運用時の監視を推奨）。
- DuckDB の日付型やバインドの挙動はバージョン依存のため、運用時は動作確認を推奨。

---

作成・修正履歴はコードから推測してまとめています。実際のリリースノートとして公開する前に、必要に応じて日付・担当者・既知のバグ等を追記してください。