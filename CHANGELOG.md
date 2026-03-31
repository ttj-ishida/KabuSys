Keep a Changelog
================

すべての注目すべき変更はこのファイルに記録します。形式は "Keep a Changelog" に準拠します。

履歴
----

### 0.1.0 - 2026-03-31

初回リリース。以下の主要機能とユーティリティを実装しました。

Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン: 0.1.0。
  - パッケージの公開インターフェースに data, strategy, execution, monitoring を想定（__all__）。

- 環境設定 / config
  - .env ファイル（.env / .env.local）および OS 環境変数からの設定自動読み込み機能を実装。
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env のパーサはシングル/ダブルクォート、バックスラッシュエスケープ、export プレフィックス、行内コメント等に対応。
  - Settings クラスを提供し、アプリ設定をプロパティ経由で取得可能：
    - J-Quants / kabu ステーション / Slack / DB パス / 監視閾値 / 実行環境 (development/paper_trading/live) / ログレベル 等を取得。
    - 必須環境変数未設定時に ValueError を発生させる _require を実装。
    - env / log_level の検証（許容値チェック）を実装。is_live/is_paper/is_dev ヘルパーあり。

- AI モジュール
  - kabusys.ai.news_nlp
    - raw_news / news_symbols を集約し、銘柄単位のニューステキストを作成。
    - ニュースウィンドウ計算（JST ベース → DB 比較用に UTC naive datetime を返す calc_news_window）。
    - OpenAI（gpt-4o-mini）を JSON Mode で呼び出して各銘柄のセンチメント（-1.0〜1.0）を取得。
    - バッチ処理（1リクエストあたり最大 20 銘柄）、記事数/文字数トリム（最大記事数・最大文字数）でトークン肥大化対策。
    - 429 / ネットワーク切断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - レスポンスの堅牢なバリデーション（JSON 復元、results 配列チェック、スコアの数値変換、未知コード無視、スコアクリップ）。
    - DuckDB への書き込みは部分失敗耐性を考慮し、取得したコードのみ DELETE → INSERT の冪等置換を実行。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能。
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError。

  - kabusys.ai.regime_detector
    - ETF 1321 の 200 日移動平均乖離（ma200_ratio）とマクロニュースの LLM センチメントを合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードで raw_news をフィルタし、LLM による macro_sentiment（-1.0〜1.0）を取得。
    - 合成スコア = clip(0.7 * MAスコア + 0.3 * macro_sentiment, -1, 1)、しきい値でラベルを付与。
    - API 呼び出しでのリトライ / バックオフ、5xx の判定・再試行、パースエラーや API 失敗時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
    - market_regime への書き込みは BEGIN / DELETE / INSERT / COMMIT を用いて冪等に実行。例外時は ROLLBACK を試行して上位へ伝搬。
    - lookahead バイアス回避のため datetime.today() 等を内部で参照しない設計（target_date を明示的に渡す）。

- データプラットフォーム（Data）
  - calendar_management
    - market_calendar テーブルを元に営業日判定ロジックを提供：is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - DB にカレンダーがない（または特定日が未登録/NULL）場合は曜日ベース（週末除外）でフォールバック。
    - next/prev_trading_day は最大探索範囲を設定して無限ループを防止。
    - calendar_update_job: J-Quants クライアントを使った差分取得 → 保存（バックフィル、健全性チェック含む）を実装。API/保存失敗時の例外ログ・安全停止の実装。

  - pipeline / etl
    - ETLResult データクラスを定義（取得数・保存数・品質問題・エラー一覧などを保持）。
    - ETL 実行での差分更新・品質チェック・バックフィル方針・id_token 注入設計を盛り込んだ骨組みを実装。
    - DuckDB との互換性考慮（executemany に空リストを渡さない等の注意点）を反映。

  - etl モジュールは pipeline.ETLResult を公開再エクスポート。

- リサーチ / ファクター
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン・200日移動平均乖離（ma200_dev）を DuckDB SQL で計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を算出。NULL 伝播・カウント制御で過小/過大評価を防止。
    - calc_value: raw_financials から最新財務を取得して PER/ROE を算出（EPS が 0 または欠損時は None）。

  - research.feature_exploration
    - calc_forward_returns: target_date から各ホライズン（デフォルト [1,5,21]）の将来リターンを一括で算出（LEAD を利用）。
    - calc_ic: factor と将来リターンの Spearman ランク相関（IC）を実装。有効サンプルが 3 未満なら None を返す。
    - rank: 同順位は平均ランクを返す実装（丸めで ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ。

- DB / 実装方針（横断）
  - DuckDB を主要な分析 DB として想定。SQL を多用してパフォーマンス重視の設計。
  - ルックアヘッドバイアス防止のため日付参照はすべて明示的な target_date を要求。
  - 外部サービス呼び出し（OpenAI / J-Quants）はフェイルセーフ設計：API 失敗はロギングして局所フォールバックか処理スキップで継続。
  - テスト容易性のため API 呼び出し部分はモック可能（_call_openai_api の差し替え等）。
  - SQL の互換性・DuckDB の仕様差分に配慮した実装（executemany 空リスト回避、list バインドの回避など）。

Security
- 環境変数（API キー等）は Settings 経由で要求されるが、コード中に平文で API キー等を埋め込まない設計。
- .env の読み込みは OS 環境変数を保護する保護セット（protected）を導入。

Notes
- 本リリースは「分析・研究・データ基盤」および「OpenAI を用いたニュース解析／レジーム判定」の基本機能を提供する初期版です。
- strategy / execution / monitoring の具象実装（発注ロジックや監視エージェントの具体的なコード）は今後のリリースで拡充予定と想定されます（__all__ に名前が含まれているため拡張ポイントあり）。
- 外部 API（J-Quants, OpenAI）との連携箇所は実運用前に API キー、ネットワーク、コスト面の評価と運用設計（レート制限・リトライポリシー）を行ってください。

Deprecated
- なし

Removed
- なし

Fixed
- なし

Closing
- 今後のリリースでは（例）
  - strategy / execution 層の実装（ブローカー連携・発注戦略）
  - 監視・アラート機能の具体化（Slack 通知等）
  - より詳細な品質チェックルールと自動修復オプション
  - ドキュメントと API の追加ユニットテスト充実化
  を計画しています。