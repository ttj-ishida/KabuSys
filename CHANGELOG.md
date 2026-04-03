CHANGELOG
=========

すべての注目すべき変更はこのファイルで管理します。  
このログは「Keep a Changelog」の形式に準拠しています。  

フォーマット:
- Added: 新規機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティに関する修正や注意点

[0.1.0] - 2026-04-03
-------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ:
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。公開 API として data, strategy, execution, monitoring をエクスポート。
- 設定・環境変数管理
  - src/kabusys/config.py
    - .env/.env.local をプロジェクトルート（.git または pyproject.toml を起点）から自動ロードする機能を追加（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサーを実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントなどを正しく処理。
    - .env のロード時に OS 環境変数を保護する仕組み（protected set）を提供。override フラグで .env.local による上書きが可能。
    - Settings クラスを提供し、J-Quants / kabuステーション / LINE / データベース / 監視 / システム関連の設定プロパティを公開。必須変数未設定時には明確な ValueError を送出。
    - KABUSYS_ENV と LOG_LEVEL のバリデーション（許容値の列挙）。
- AI（NLP）モジュール
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）に JSON Mode でバッチ送信してセンチメントを算出する処理を実装。
    - 特徴:
      - JST ベースのニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
      - 銘柄ごとに最新記事を最大 N 件（_MAX_ARTICLES_PER_STOCK）・文字数でトリムしてプロンプト化。
      - 1 API コールで最大 _BATCH_SIZE 銘柄を送信するチャンク処理。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
      - レスポンスの堅牢なバリデーション（JSONモードの前後ノイズ復元、results/code/score の検証、数値チェック、±1.0 でクリップ）。
      - 書き込みは idempotent（対象コードのみ DELETE → INSERT）で部分失敗時に既存データを保護。
      - テスト容易性のため _call_openai_api を patch 可能に実装。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（225連動型）の 200 日移動平均乖離（重み70%）と、マクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出する機能を実装。
    - 特徴:
      - ma200_ratio は target_date 未満のデータのみ使用してルックアヘッドを防止。データ不足時は中立（1.0）を返すフェイルセーフ。
      - マクロ記事はキーワードフィルタで抽出し、最大件数で LLM 評価。API 失敗時は macro_sentiment=0.0 にフォールバック。
      - レジームスコア合成後に market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試みて例外を伝播。
      - OpenAI 呼び出し用に専用の _call_openai_api を実装し、news_nlp と結合しない設計（モジュール分離）。
- データプラットフォーム（Data）
  - calendar_management.py
    - JPX 市場カレンダーの管理と夜間更新ジョブ（calendar_update_job）を実装。
    - 提供するユーティリティ:
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
    - 設計上の挙動:
      - market_calendar が未取得なら曜日ベースでフォールバック（土日を休業日扱い）。
      - DB 登録ありの場合は DB 値優先、未登録日は曜日フォールバックで一貫した結果を返す。
      - 最大探索日数やバックフィル、健全性チェック（極端な未来日付発見時のスキップ）を実装。
    - calendar_update_job は J-Quants クライアントを利用して差分取得・保存し、バックフィル日数分を再取得して API 側の修正を吸収する。
  - pipeline.py / etl.py
    - ETL のエントリ／データ構造を実装。
    - ETLResult データクラスを追加（取得数・保存数・品質問題リスト・エラーリスト・ユーティリティ to_dict を提供）。
    - ETL の方針:
      - 差分更新、backfill による後出し修正吸収、品質チェックは Fail-Fast ではなく検出結果を集約して呼び出し元に委譲。
      - jquants_client を用いた idempotent な保存（ON CONFLICT / upsert 想定）。
    - src/kabusys/data/__init__.py から ETLResult を公開（etl.py）。
- 研究用モジュール（Research）
  - src/kabusys/research/*
    - factor_research.py:
      - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）およびバリュー（PER, ROE）計算を実装。
      - DuckDB 上で SQL とウィンドウ関数を使用して効率的に計算。データ不足時は None を返す保守的設計。
      - 外側に対して (date, code) をキーとする dict リストを返す。
    - feature_exploration.py:
      - 将来リターンの計算（任意ホライズン、デフォルト [1,5,21]）、IC（スピアマンのランク相関）計算、ファクター統計サマリー、ランク化ユーティリティを実装。
      - ランク計算は同順位（ties）を平均ランクで扱う。horizons 引数は検証済み。
    - research パッケージ __init__ で主要 API を再エクスポート。
- テスト・運用性を意識した設計
  - OpenAI 呼び出し関数や内部待機（time.sleep）等は patch による差替えが容易な実装にしてあり、ユニットテストでのモックが可能。
  - DuckDB に対する executemany 呼び出しについて互換性・空リスト対策（空パラメータを送らない）を考慮。

Changed
- 初版のため特定の「変更」はなし（これまでの開発履歴を集約した初回公開）。

Fixed
- 初版のため特定の「修正」はなし。

Security
- OpenAI API キーおよび各種機密情報は Settings 経由で取得する設計。必須の機密情報が未設定の場合は ValueError を明示的に投げ、誤った動作や鍵の漏洩を防ぐ（ログにはキー本体を出力しない想定）。

Notes / 既知の設計上のフェイルセーフ
- AI 系処理で API が利用できない場合は:
  - news_nlp: 該当チャンクはスキップ、取得済みスコアのみ DB に書き込む（部分成功を許容）。
  - regime_detector: macro_sentiment=0.0 にフォールバックして計算を継続。
- データ不足（移動平均に必要な行数が不足等）の場合は中立値(None/1.0/スキップ)で扱うことで運用中の致命的障害を回避。
- すべての日付処理はルックアヘッドバイアス防止のため、内部で date.today()/datetime.today() を直接参照しない方針（target_date 引数で明示的に制御）。

将来の改善案（参考）
- news_nlp / regime_detector の出力検証をより厳密化する（スキーマ検証やJSON Schema 導入）。
- ETL パイプラインのジョブ管理・リトライ・監査ログの統合（Airflow 等との連携）。
- ai モジュールのモデル切替を容易にする設定化（モデル名を環境変数化）。

問い合わせ
- 本 CHANGELOG はコードベースから推測して作成しています。実際のリリースノートやドキュメントに追加したい点があれば指示してください。