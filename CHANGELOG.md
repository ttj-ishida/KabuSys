CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記載します。本プロジェクトは Keep a Changelog の形式に準拠しています。
リリースごとの要約を日本語で記載しています。

[0.1.0] - 2026-04-02
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージメタ情報:
    - src/kabusys/__init__.py に __version__ = "0.1.0" を導入。
    - パッケージ公開対象: data, strategy, execution, monitoring（__all__）。
- 環境設定管理
  - src/kabusys/config.py
    - .env/.env.local ファイルおよび環境変数から設定を自動読み込みする仕組みを追加。
    - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env パーサを実装:
      - "export KEY=val" 形式対応。
      - シングル／ダブルクォート内のバックスラッシュエスケープ対応。
      - クォート無しの値に対するインラインコメント処理（直前が空白／タブの場合）。
      - 不正行は無視。
    - 環境変数取得ユーティリティ Settings を追加（必須キー取得時は未設定で ValueError を投げる）。
    - KABUSYS_ENV / LOG_LEVEL の値検証（許容値セット）を実装。
    - 各種パス・閾値などの設定プロパティ（duckdb/sqlite パス、監視閾値、PID ファイル等）。
- AI モジュール（ニュース NLP / レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI (gpt-4o-mini) の JSON Mode を用いて銘柄ごとのセンチメントを算出する機能を追加。
    - バッチ処理: 1 API コールあたり最大 20 銘柄（_BATCH_SIZE）。
    - 1 銘柄あたりのトークン肥大対策: 最新記事最大 10 件、最大 3000 文字でトリム。
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。
    - レスポンス検証: JSON パース回復処理（外側の余計なテキスト除去）、results キー/型/コード整合性/数値性をチェック。スコアは ±1.0 にクリップ。
    - 書き込みは部分失敗時に既存スコアを保護するため、対象コードのみ DELETE → INSERT（トランザクション）で置換。
    - time window 計算: JST 基準の前日 15:00 ～ 当日 08:30 を UTC に変換して DB クエリに利用する calc_news_window を提供。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する機能を追加。
    - ma200_ratio 計算は target_date 未満のデータのみを使用しルックアヘッドを防止。データ不足時は中立 (1.0) として続行。
    - マクロ記事はキーワードでフィルタし最大 20 件まで評価。記事なし時は LLM 呼び出しをスキップして macro_sentiment = 0.0。
    - OpenAI 呼び出し失敗時はフォールバック（macro_sentiment = 0.0）で継続し、例外は基本的に外に出さない設計（ただし DB 書込失敗時は例外伝播）。
    - 判定結果は market_regime テーブルへ冪等に書き込む（BEGIN / DELETE / INSERT / COMMIT）。
- Data モジュール（カレンダー・ETL・パイプライン）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理: market_calendar を基に is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - DB にデータがない場合は曜日ベースのフォールバック（週末を非営業日）を採用。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等更新。バックフィルと健全性チェックを実装。
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETL パイプラインの基本構造を実装。差分取得・保存・品質チェックの設計に対応。
    - ETLResult dataclass を実装（target_date, fetched/saved counts, quality_issues, errors 等）。to_dict による辞書化を提供。
    - etl.py で pipeline.ETLResult を再エクスポート。
  - src/kabusys/data/__init__.py として data パッケージを整理。
- Research モジュール
  - src/kabusys/research/factor_research.py
    - Momentum / Volatility / Value / Liquidity に関する定量ファクター計算を実装:
      - calc_momentum: 1M/3M/6M リターン、ma200_dev（200 日移動平均乖離）を計算。
      - calc_volatility: 20 日 ATR, 相対 ATR, 20 日平均売買代金, 出来高比率を計算。
      - calc_value: raw_financials から最新財務を取得し PER / ROE を計算。
    - DuckDB 内の SQL ウィンドウ関数を活用し、データ不足時は None を返す設計。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: target_date から指定ホライズン（デフォルト [1,5,21]）の将来リターンを取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - rank / factor_summary 実装: ties の平均ランク処理、統計サマリー（count/mean/std/min/max/median）。
  - src/kabusys/research/__init__.py で主要関数を再エクスポート。
- その他
  - src/kabusys/ai/__init__.py と src/kabusys/research/__init__.py で主要 API を __all__ にて公開。

Changed
- OpenAI 呼び出しの実装方針を明確化:
  - news_nlp と regime_detector のそれぞれで独立した _call_openai_api 実装を採用。テスト時に patch しやすいように設計。
- DuckDB とのトランザクション書き込みは冪等性を重視（DELETE → INSERT、部分的な上書きで既存データ保護）。

Fixed
- （初版のため既知の軽微なロジック調整は今後のマイナーで対応予定）

Deprecated
- なし

Removed
- なし

Security
- 機密情報の取り扱い:
  - OpenAI API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY から取得。未設定時は ValueError を投げて明示する設計。
  - .env の自動読み込みは OS 環境変数を保護するため protected set を使用し、.env / .env.local の上書きを制御。

注意事項 / 既知の問題
- pipeline._get_max_date のソースが途中で途切れている（ファイル末尾付近に "return date.fro" のような不完全な行が存在）。現状だと当該関数が正しく動作しない可能性があります。次回リリースで修正予定。
- OpenAI 呼び出しは外部 API に依存するため、API 料金や利用制限、レスポンスの仕様変更により振る舞いが変わる可能性があります。429 / ネットワーク断 / タイムアウト / 5xx をリトライ対象としていますが、非 5xx APIError はリトライしない方針です。
- ETL / カレンダーのジョブは J-Quants クライアント（jquants_client）に依存します。J-Quants 側の仕様変更・障害時は ETL が影響を受けます。
- datetime.today() / date.today() を直接参照する箇所は極力排し、target_date を明示的に渡す設計によりルックアヘッドバイアスを防止しています。ジョブ運用時は必ず適切な target_date を指定してください。

貢献・フィードバック
- バグ報告、改善提案、パッチは GitHub の Issue / PR を通じて歓迎します。特に pipeline/_get_max_date の修正は優先度高めです。

----- End of CHANGELOG -----