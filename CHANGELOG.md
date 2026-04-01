CHANGELOG
=========
すべての重要な変更はここに記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。  

[0.1.0] - 2026-04-01
--------------------

Added
- 初期リリース: KabuSys 日本株自動売買システムの基礎モジュール群を追加。
  - パッケージ公開情報
    - パッケージバージョンを __version__ = "0.1.0" として定義。パッケージ外部公開の __all__ を設定。
- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数を読み込む自動ロード機能を実装。
  - プロジェクトルート検出ロジックを導入（.git または pyproject.toml を起点に探索、CWD に依存しない）。
  - .env パーサーを実装:
    - コメント行、空行スキップ、export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - クォート無し値のインラインコメント処理（直前がスペース/タブの '#' をコメントとみなす）。
    - ファイル読み込み時の protected キー（OS 環境変数保護）と override オプションをサポート。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - Settings クラスを実装し、アプリケーション設定をプロパティ経由で取得:
    - J-Quants / kabu / Slack / DB パス / 監視閾値 / 環境 (development/paper_trading/live) / ログレベル 等。
    - 必須環境変数未設定時は ValueError で明確にエラー通知。
    - env / log_level のバリデーションを実装。
- AI 関連 (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news):
    - raw_news と news_symbols を元に銘柄毎にニュースを集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメントを算出。
    - バッチサイズ、1銘柄あたりの記事数上限、文字数トリム、UTC/JST ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を実装。
    - API 呼び出しに対して 429/ネットワーク断/タイムアウト/5xx を対象に指数バックオフでリトライ。
    - レスポンス検証ロジック（JSON 抽出、results キーの検証、コード照合、数値判定、スコアのクリップ）を実装。
    - 成功した銘柄のみ ai_scores テーブルに冪等的に（DELETE → INSERT）書き込む実装。
    - API キー注入（引数 or OPENAI_API_KEY 環境変数）をサポート。未設定時は明確に ValueError を送出。
  - 市場レジーム判定 (regime_detector.score_regime):
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - prices_daily から ma200_ratio を計算（target_date 未満のデータのみを使用してルックアヘッドを回避）。
    - raw_news からマクロキーワードでタイトルを抽出し、OpenAI へ投げて macro_sentiment を取得（記事無しまたは API 失敗時は 0.0 をフェイルセーフに採用）。
    - スコア合成後 market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - OpenAI 呼び出しは news_nlp と独立した実装とし、モジュール結合を避ける設計。
- 研究（research）モジュール
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離を算出。データ不足時は None を返す設計。
    - calc_volatility: 20 日 ATR（true range の扱いに注意）、相対 ATR、20 日平均売買代金、出来高比率を算出。
    - calc_value: raw_financials の最新財務データと prices_daily を組み合わせて PER, ROE を算出（EPS が 0/欠損時は None）。
    - DuckDB ベースの SQL ウィンドウ関数を用いた高効率実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）に対する将来リターンを一括取得。horizons の入力チェックあり。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装（records の結合、None の除外、最少レコード数チェック）。
    - rank: 平均ランク（同順位は平均ランク）を返すユーティリティ（浮動小数の丸めで ties 検出漏れを防止）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - research パッケージは zscore_normalize を data.stats から再エクスポート。
- データプラットフォーム（data）
  - calendar_management:
    - JPX カレンダー管理ユーティリティを実装: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar が未登録の場合は曜日ベース（平日を営業日）でフォールバックする一貫した挙動。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等に更新（lookahead / backfill / 健全性チェックを実装）。
    - 最大探索範囲・バックフィル・健全性の安全措置を導入して無限ループや異常データを回避。
  - ETL / pipeline:
    - ETLResult データクラスを実装して ETL 処理結果を構造化（品質問題リスト、エラーリストを含む）。
    - ETLResult.to_dict() により監査ログ向けの辞書化をサポート。
    - pipeline モジュールにおけるテーブル存在チェックや最大日付取得などのユーティリティを実装（差分更新と backfill を想定した設計）。
  - etl.py では pipeline.ETLResult を公開インターフェースとして再エクスポート。
- テスト/開発向け設計配慮
  - datetime.today()/date.today() を直接参照しない設計（ルックアヘッドバイアス回避）。target_date を明示的に渡して determinism を確保。
  - OpenAI 呼び出しの内部関数はテスト時に patch しやすいように分離している（unittest.mock.patch で差替え可能）。
  - API 失敗時はフェイルセーフ挙動（ニューススコア・マクロセンチメントは 0.0、処理は継続）を採用し、部分失敗時に既存 DB データを保護する設計（書き込み対象を限定する戦略）。

Changed
- （新規初期リリースのため該当なし）

Fixed
- （新規初期リリースのため該当なし）

Security
- OpenAI API キー・Slack 等の機密情報は環境変数経由で取得し、Settings で必須チェックを行うことで明示的な設定を要求。

Notes / Known issues
- pipeline._get_max_date の実装の末尾に不完全なトークン（ソース断片）が見られます。リリース版ではこの関数の最終行の記述ミスを修正する必要があります（現状だと NameError/構文エラーを引き起こす可能性があります）。
- DuckDB の executemany 周りの挙動に依存する箇所（空リスト不可等）を考慮して実装していますが、使用する DuckDB のバージョン差異に注意してください。
- OpenAI 依存部分は外部 API 呼び出しのため、API 仕様変更やレート制限により挙動が変わる可能性があります。テスト用に API 呼び出しをモックする手順を推奨します。

ライセンスやメンテナンス方針、マイグレーションノート等は今後のリリースで追記予定です。