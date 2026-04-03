CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-03
-------------------

Added
- 基本パッケージ初期実装を追加
  - パッケージ名: kabusys（src/kabusys/__init__.py）
    - __version__ を "0.1.0" として公開。主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。
- 環境設定管理を追加（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートの検出は .git または pyproject.toml を基準に行うため、CWD に依存しない動作。
    - 環境変数の自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env と .env.local の読み込み順（OS環境 > .env.local > .env）と、.env.local の上書き動作をサポート。
  - .env のパースを堅牢化（コメント、export プレフィックス、クォート・エスケープ処理、インラインコメント処理など）。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB /監視 / システム関連の設定項目をプロパティで公開。
  - 必須環境変数未設定時に明確な ValueError を送出する _require を実装。
  - KABUSYS_ENV / LOG_LEVEL の値検証を実装（許容値チェック）。
- AI モジュールを追加（src/kabusys/ai/）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとのニュースを生成し、OpenAI（gpt-4o-mini、JSON Mode）でセンチメントを取得して ai_scores テーブルへ保存。
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）計算ユーティリティ calc_news_window を実装。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大対策（記事数・文字数制限）、レスポンス検証、スコアの ±1.0 クリップを実装。
    - レート制限、ネットワーク断、タイムアウト、5xx を対象とした指数バックオフによるリトライロジックを実装。致命的でない失敗はスキップして継続するフェイルセーフ設計。
    - DuckDB executemany の互換性（空リストバインド回避）を考慮して DB 書き込みを設計。
    - API 呼び出し部はテスト時に差し替え可能（ユニットテスト向け patch ポイント）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュースベースのマクロセンチメント（重み 30%）を合成して日次の market_regime を算出・保存。
    - prices_daily, raw_news, market_regime テーブルを使用。DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）。
    - LLM 呼び出しは gpt-4o-mini（JSON Mode）を使用。API エラー時はマクロスコアを 0.0 にフォールバックするフェイルセーフを実装。
    - ルックアヘッドバイアス防止の設計（date.today() を直接参照しない、prices_daily クエリに date < target_date の排他条件）。
- Research モジュールを追加（src/kabusys/research/）
  - factor_research（src/kabusys/research/factor_research.py）
    - モメンタム (calc_momentum): 1M/3M/6M リターン、200 日 MA 乖離を計算。データ不足時は None を返す挙動。
    - ボラティリティ/流動性 (calc_volatility): 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。NULL 伝播を考慮した true_range 計算。
    - バリュー (calc_value): raw_financials の最新財務データを使って PER、ROE を計算。EPS が 0/NULL の場合は per を None とする。
    - DuckDB 上で SQL+ウィンドウ関数を用いて効率的に算出。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算 (calc_forward_returns): 複数ホライズン（デフォルト [1,5,21]）のリターンを一括クエリで取得。ホライズン検証（正の整数 ≤ 252）を実装。
    - IC 計算 (calc_ic): スピアマンランク相関（ランクは平均ランクで ties 処理）を実装。有効レコードが 3 件未満の場合は None を返す。
    - ランク変換 util (rank): 値をランクに変換（同順位は平均ランク）。丸め処理で浮動小数点の ties 誤検出を防止。
    - 統計サマリー (factor_summary): count/mean/std/min/max/median を標準ライブラリのみで計算。
  - research パッケージ __all__ に主要関数を公開。
- Data モジュールを追加（src/kabusys/data/）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを参照して is_trading_day/is_sq_day 判定、next_trading_day/prev_trading_day/get_trading_days の実装。
    - DB にデータがない場合は曜日ベースのフォールバック（週末を非営業日）を採用。DB 値がある場合はそれを優先して一貫性を担保。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等書き込み。バックフィル・健全性チェック（将来日付の異常検出）を実装。
    - 最大探索日数やバックフィル日数などの保護設定を導入（無限ループや過度な API 呼び出し防止）。
  - ETL パイプライン（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）
    - ETLResult データクラスを追加（ETL 成果の構造化、品質問題・エラーの集約、has_errors / has_quality_errors プロパティ、to_dict メソッド）。
    - pipeline モジュールから ETLResult を再エクスポートするための etl モジュールを追加。
    - 差分更新方針、backfill のデフォルト値、品質チェック方針（Fail-Fast ではなく全件収集）をドキュメントに反映。
    - DuckDB のテーブル存在チェック等のユーティリティを実装。
- パッケージ公開点とテスト容易性
  - AI モジュール内の OpenAI 呼び出しは内部ラッパー関数経由にしており、unittest.mock.patch で差し替え可能（ユニットテスト支援）。
  - DB 書き込みは部分失敗時に既存データを消さない設計（対象 code を限定した DELETE→INSERT）など、実運用を想定した安全策を導入。

Changed
- 初版リリースにつき該当なし。

Fixed
- 初版リリースにつき該当なし。

Security
- OpenAI / 外部 API キー未設定時は ValueError を発生させ、明示的にキーを要求するようにした（誤動作を未然に防止）。

Notes / Migration / Usage
- 各公開関数（score_news, score_regime, calc_momentum 等）は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）と target_date（datetime.date）を引数に取ります。内部で datetime.today() を参照しない設計のため、テスト時は任意の日付を与えて determinisitic に動作させることができます。
- OpenAI 呼び出しには環境変数 OPENAI_API_KEY または関数引数での api_key 注入が必要です。
- .env の自動ロードはプロジェクトルートが検出できた場合のみ行われます。CI / テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- DuckDB 書き込みは冪等化を意識しており、部分的に失敗した際にも既存データを不用意に削除しないよう設計されています。

開発者向けメモ
- OpenAI 依存部は将来的に別のプロバイダに差し替えることを想定して抽象化されています。テストでは内部の _call_openai_api を patch してください。
- DuckDB バージョン依存の挙動（LIST バインド、executemany の空リストなど）に配慮した実装になっています。

--- 

今後の予定（例）
- strategy / execution / monitoring の具象実装（発注ロジック、実行監視、LINE 通知など）
- ai/regime_detector の精度改善（キーワード/プロンプトのチューニング、モデル切替）
- ETL の並列化や差分取得ロジックの最適化

（この CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時にはコミット履歴やリリース手順に基づく補足を推奨します。）