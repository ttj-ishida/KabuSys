CHANGELOG
=========

すべての注目すべき変更点を記載します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。

[0.1.0] - 2026-03-29
-------------------

Added
- 初回公開リリース (0.1.0) — 日本株自動売買システム "KabuSys" の基本機能を実装・公開。
- パッケージ基盤
  - src/kabusys/__init__.py: パッケージのエントリポイントと __version__ を追加。data, strategy, execution, monitoring を公開モジュールとして定義。
- 設定 / 環境変数管理
  - src/kabusys/config.py:
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする仕組みを実装。OS 環境変数を保護する保護リスト（protected）により上書きを制御。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env ファイルのパース: export 句対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの取り扱いなどを実装。
    - Settings クラス: 必須環境変数取得（_require）、各種設定プロパティ（J-Quants / kabuAPI / Slack / DB パス / 環境・ログレベル検証）を追加。環境値検証（KABUSYS_ENV, LOG_LEVEL）と利便性プロパティ（is_live 等）を提供。
- データプラットフォーム
  - src/kabusys/data/calendar_management.py:
    - JPX カレンダー管理と営業日ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得の場合は曜日ベースでフォールバックする堅牢な実装。
    - calendar_update_job: J-Quants API から差分取得 → 冪等保存（ON CONFLICT / 上書き）を行う夜間バッチ用関数、バックフィル／健全性チェックを実装。
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py:
    - ETLResult データクラスを公開（ETL の取得数・保存数・品質問題・エラー収集を保持）。
    - ETL パイプライン用ユーティリティ（テーブル存在チェック、最大日付取得、差分処理方針）を実装。DuckDB の制約（executemany の空リスト不可等）に配慮した実装。
- 研究用モジュール（Research）
  - src/kabusys/research/factor_research.py:
    - モメンタム / ボラティリティ / バリュー系ファクター計算関数を実装:
      - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日 MA 乖離）を計算。データ不足時は None を返す。
      - calc_volatility: 20日 ATR（atr_20/atr_pct）、20日平均売買代金、volume_ratio を計算。
      - calc_value: raw_financials から最新財務を取得し PER/ROE を計算。
    - DuckDB SQL ベースで計算し、外部 API など副作用なしで利用可能。
  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns: 指定ホライズンの将来リターン (fwd_1d/fwd_5d/fwd_21d 等) を一括取得する汎用機能。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を実装。入力件数不足時には None を返す。
    - rank: 同順位は平均ランクで処理（丸め誤差対策で round を使用）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
  - src/kabusys/research/__init__.py: 主要関数を再公開。
- AI / ニュース解析
  - src/kabusys/ai/news_nlp.py:
    - ニュース記事を銘柄ごとに集約し OpenAI（gpt-4o-mini）の JSON モードでセンチメントスコアを取得、ai_scores テーブルに書き込むフローを実装。
    - calc_news_window: JST ベースのニュース収集ウィンドウ計算（前日 15:00 〜 当日 08:30 JST を UTC に変換）。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/回）、1銘柄あたりの文字数制限／記事数制限、レスポンスのバリデーション（JSON 抽出、results/key/type/score チェック）、スコアクリップ（±1.0）を実装。
    - API エラー（429/ネットワーク/タイムアウト/5xx）は指数バックオフでリトライ、その他はスキップするフェイルセーフ設計。
    - DuckDB の制約（executemany に空リスト不可）に対応した安全な書き込みロジックを実装。
  - src/kabusys/ai/regime_detector.py:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込む機能を実装。
    - _calc_ma200_ratio（ルックアヘッド回避のため target_date 未満のデータのみ使用、データ不足時は中立扱い）、_fetch_macro_news（キーワードフィルタ）、_score_macro（OpenAI 呼び出し、リトライ/フォールバック）を実装。
    - OpenAI 呼び出しは JSON モード / gpt-4o-mini、レスポンスパース失敗や API 問題時には macro_sentiment=0.0 とするフェイルセーフ動作。
    - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等処理を行い、失敗時は ROLLBACK を試行。
  - src/kabusys/ai/__init__.py: score_news をエクスポート。
- テスト・拡張性への配慮
  - OpenAI 呼び出しを行う内部関数（news_nlp._call_openai_api, regime_detector._call_openai_api）をモック置換しやすく設計し、ユニットテストが容易。
  - 主要処理は datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取ることでルックアヘッドバイアスを防止する設計。

Changed
- N/A（初回リリースのため変更履歴はなし）

Fixed
- N/A（初回リリースのため修正履歴はなし）

Deprecated
- N/A

Removed
- N/A

Security
- N/A

Notes / Implementation details（設計上の重要点）
- DuckDB 互換性:
  - executemany に空リストを渡せない問題など DuckDB の実装差分に配慮した実装（空チェックを行い必要時のみ executemany を呼ぶ）。
  - 日付の取り扱いは date 型で統一し、DB からの値は安全に変換するユーティリティを提供。
- フェイルセーフ設計:
  - 外部 API（OpenAI, J-Quants）が失敗しても処理を継続する（スコアは 0.0、該当銘柄はスキップ等）方針を採用。
- ロギング:
  - 各主要処理に対して info/debug/warning/exception ログを適切に出力。
- 環境設定:
  - 自動 .env ロード時に OS 環境変数の保護（上書き防止）を行うため、ローカル .env ファイルが開発環境の設定を壊すリスクを低減。

今後の予定（想定）
- strategy / execution 周りの注文ロジック・バックテスト機能の追加。
- モデル改善や LLM プロンプトチューニング、ニュース集合方法の改善。
- より細かい ETL ジョブ制御と監視（monitoring）機能拡充。

--- 

（注）本 CHANGELOG は与えられたコードベースの内容から実装意図・設計方針を推測して作成しています。実際の変更履歴（コミット履歴）に基づくものではありません。