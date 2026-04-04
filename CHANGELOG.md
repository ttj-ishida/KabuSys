CHANGELOG
=========

すべての注目すべき変更はここに記載します。  
このファイルは "Keep a Changelog" の形式に準拠しています。  

Unreleased
----------


[0.1.0] - 2026-04-04
--------------------

追加 (Added)
- 初回リリース: kabusys パッケージ v0.1.0
  - パッケージ公開情報:
    - src/kabusys/__init__.py によりパッケージ名と __version__="0.1.0" を設定。
    - public API として data, strategy, execution, monitoring をエクスポート。

- 環境変数 / 設定管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロードの無効化をサポート（テスト用途）。
  - .env パーサ実装:
    - export KEY=val 形式、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理に対応。
    - 無効行やキー不在行を無視。
  - _load_env_file による上書き制御と protected（OS 環境変数保護）サポート。
  - Settings クラスを提供（settings インスタンスで利用可能）:
    - J-Quants / kabuステーション / LINE Messaging / データベースパス / 監視設定 / システム設定（KABUSYS_ENV, LOG_LEVEL）等のプロパティ。
    - env と log_level の入力検証（許容値の列挙）とヘルパー is_live/is_paper/is_dev。
    - 既定値や Path への展開、閾値（CPU/MEM/DISK）等の型変換を実装。
    - 必須変数未設定時は _require が ValueError を投げる挙動を明示。

- AI 関連機能 (src/kabusys/ai)
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols を集約して銘柄ごとに LLM（gpt-4o-mini）でセンチメントを算出し ai_scores に書き込む。
    - ニュース時間ウィンドウ計算（前日15:00 JST〜当日08:30 JST 相当）を calc_news_window で提供。
    - 1 銘柄あたりの最大記事数・文字数制限、銘柄バッチサイズ（最大 20）を採用しトークン肥大化を抑制。
    - OpenAI 呼び出し時のリトライ（429・接続断・タイムアウト・5xx）と指数バックオフ、失敗フォールバック（スキップ）を実装。
    - レスポンス検証ロジック（JSON 抽出、results 配列・各要素の code/score バリデーション、スコアの ±1 クリップ）。
    - テスト用に OpenAI 呼び出し部分を _call_openai_api で切り出し、モック差し替えが可能。
    - 書き込みは部分失敗に備えコード絞込み（DELETE → INSERT）で冪等性を確保。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日 MA 乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して market_regime に日次で保存。
    - ma200 比率計算は target_date 未満のデータのみ使用してルックアヘッドバイアスを防止。データ不足時は中立値 1.0 を採用。
    - マクロニュース抽出はキーワードベースでフィルタ（最大 20 件）。ニュースが無ければ LLM 呼び出しをスキップして macro_sentiment=0.0。
    - OpenAI 呼び出しは独立した _call_openai_api を使用、リトライ・エラー処理・レスポンスパースのフォールバックを実装。
    - スコア合成後、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書込み失敗時には ROLLBACK を行い例外を上位へ伝播。
    - しきい値とラベル付け（bull/neutral/bear）を明確化。

- データ処理・ETL・カレンダー (src/kabusys/data)
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダーの夜間更新ジョブ calendar_update_job を実装（J-Quants API から差分取得 → 保存）。
    - market_calendar の有無により DB 値優先、未登録日は曜日ベースのフォールバック（週末除外）で一貫した is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - 最大探索日数やバックフィル、健全性チェック（極端な将来日付はスキップ）などの安全策を実装。
    - DuckDB からの型変換ユーティリティ、テーブル存在チェックを提供。

  - ETL パイプライン（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）
    - ETLResult データクラスを導入。取得件数・保存件数・品質問題・エラー概要を保持。has_errors / has_quality_errors / to_dict を提供。
    - 差分更新の方針、backfill のデフォルト等設計方針を実装方針として明記（実際の ETL フローは jquants_client と quality モジュールに依存）。
    - データ保存は idempotent を想定（save_* 関数で ON CONFLICT DO UPDATE を利用する設計）。

- リサーチ / ファクター計算 (src/kabusys/research)
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す設計。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。NULL 伝播を慎重に扱う。
    - calc_value: raw_financials から最新財務（report_date <= target_date）を取得し PER / ROE を算出（EPS 不在/0 は None）。
    - 全関数は DuckDB の prices_daily / raw_financials のみ参照し、外部 API 呼び出しを行わない。

  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。horizons の入力検証あり。
    - calc_ic: スピアマン（ランク）相関で IC を計算。データ不足（<3 件）の場合は None。
    - rank / factor_summary: ランク化（同順位は平均ランク）、各カラムの基本統計量（count/mean/std/min/max/median）を実装。
    - 標準ライブラリのみでの実装を採用し pandas 等に依存しない設計。

- その他
  - DuckDB を主要な内部データベースとして利用する前提で SQL＋Python のハイブリッド実装を多用。
  - ロギングを各モジュールに導入し、警告・情報ログで問題を明示。
  - ルックアヘッドバイアス回避のため、score/regime/news 等のコア関数は datetime.today()/date.today() を内部参照しない（target_date を外部から注入する設計）。
  - OpenAI API 呼び出しに関してはテストしやすさを考慮して呼び出し箇所を抽象化（モック差し替え可能）。

変更 (Changed)
- 初回リリースのため該当なし。

修正 (Fixed)
- 初回リリースのため該当なし。

既知の注意点（ドキュメント的補足）
- OpenAI API キー未設定時は score_news / score_regime が ValueError を投げる。
- DuckDB の executemany に空リストを渡すと問題になるため、空チェックを行ってから実行する実装になっている（互換性のための配慮）。
- 一部の挙動（例: .env のパース細部、LLM レスポンスの不確実性対応）は設計文書内に明示されたフォールバック戦略に従う。

今後の予定（例）
- 監視・実行部分（execution/monitoring）の詳細実装の公開・テストカバレッジ充実。
- J-Quants / kabu ストリーミングや実取引連携の追加実装（安全策の強化）。
- AI モデルの差し替え・設定の外部化（モデル名・温度・レスポンスフォーマットの柔軟化）。

----------------------------------------
（この CHANGELOG はコード内容から推測して作成しています。実際のリリースノートと差異がある場合があります。）