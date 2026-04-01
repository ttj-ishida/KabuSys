# CHANGELOG

このファイルは Keep a Changelog の形式に準拠しています。  
リリース日付はコードベースから推測したものを使用しています。

全ての変更はセマンティックバージョニングに従います。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-01
初期リリース

### 追加
- 全体
  - パッケージ初回公開。モジュール群を整理して公開 API を定義（kabusys パッケージ、__all__ に data/strategy/execution/monitoring を追加）。
  - DuckDB をデータバックエンドとして利用する設計に基づくデータ処理基盤を実装。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび OS 環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
  - 重要な設定値へアクセスする Settings クラスを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN 等の必須環境変数チェックを含む）。
  - ログレベルと実行環境(env: development/paper_trading/live) のバリデーションを実装。
  - パス設定（duckdb/sqlite/pid ファイル等）や監視閾値（CPU/メモリ/ディスク）を環境変数から取得するプロパティを追加。

- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメント（-1.0〜1.0）を評価。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）用の calc_news_window を実装（UTC に変換した naive datetime を返す）。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたりの最大記事数／文字数制限、レスポンス検証ロジックを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライする仕組みを実装。部分成功時は成功分のみ ai_scores テーブルに置換（DELETE → INSERT）。
    - テスト容易性のため OpenAI 呼び出しを _call_openai_api に分離し、 unittest.mock.patch による差し替えを想定。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出し market_regime テーブルへ冪等的に書き込み。
    - ma200_ratio 算出（target_date 未満のデータのみ使用してルックアヘッドを防止）、マクロ記事収集、OpenAI 呼び出し、合成スコアの閾値判定を実装。
    - OpenAI 呼び出し失敗時は macro_sentiment=0.0 へフォールバックして処理を続行するフェイルセーフ実装。
    - news_nlp とは別実装の _call_openai_api を用いることでモジュール結合を回避（テスト差し替え可能）。

- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar テーブルに基づく営業日判定 API（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）を提供。
    - DB 登録値がない場合は曜日ベース（土日除外）でフォールバックする一貫したロジックを実装。
    - calendar_update_job を実装し、J-Quants API から差分取得して冪等的に保存（バックフィルと健全性チェック付き）。

  - ETL パイプライン基盤（pipeline）
    - ETL 実行結果を表す ETLResult データクラスを実装（取得件数・保存件数・品質チェック結果・エラー一覧を保持、辞書化メソッド含む）。
    - 差分更新・バックフィル・品質チェック用のユーティリティを実装するための基礎を提供。
    - 一部ユーティリティ関数（テーブル存在チェック、最大日付取得など）を実装。
    - kabusys.data.etl で ETLResult を再エクスポート。

- リサーチ（kabusys.research）
  - factor_research
    - momentum / volatility / value といった定量ファクター計算関数を実装（prices_daily / raw_financials を参照）。
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離などを計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比などを計算。NULL 伝播を考慮した実装。
    - calc_value: raw_financials から最新財務を結合して PER / ROE を算出。
    - 全関数は DB 内の SQL ウィンドウ関数を有効活用して高速に集計する設計。

  - feature_exploration
    - calc_forward_returns: 指定日から各ホライズン先の将来リターンを一括取得する汎用実装（ホライズン検証あり）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算するユーティリティ。
    - rank / factor_summary: ランク化・統計サマリー（count/mean/std/min/max/median）を提供。
    - pandas 等外部依存を避け、標準ライブラリのみで実装。

### 変更
- なし（初回リリース）

### 修正 / 安定化
- .env パーサを堅牢化
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント判定（クォート有無での挙動差）に対応。
- OpenAI 呼び出しの耐障害性強化
  - 429 / 接続エラー / タイムアウト / 5xx に対してリトライ実装（指数バックオフ）と、最終的にフェイルセーフでゼロスコアにフォールバックする方針を採用。
- DuckDB 互換性考慮
  - executemany に空リストを渡すと失敗する（DuckDB 0.10 の仕様）ため、空チェックを追加してから executemany を呼ぶ実装に変更。
- DB 書き込みは冪等設計
  - market_regime / ai_scores などで既存レコードを削除してから挿入する手順を採用し、部分失敗時に既存データを不必要に削除しない実装。

### セキュリティ
- 環境変数の上書き保護機能を実装
  - .env 読み込み時、override=True でも OS 環境変数（起動時の os.environ のキーセット）を protected として上書き不可にするオプションを導入。
- 必須 API キーは明示的にチェックし、未設定時は ValueError を投げる（OpenAI / Slack / Kabu API / J-Quants の主要トークン）。

### 既知の問題 / 注意事項
- pipeline._get_max_date の末尾が不完全（typo のように見える `return date.fro` が含まれている断片が存在）：
  - コードスニペットの末端で関数が途中で切れているため、この部分は実装ミスまたはファイル切り取りの影響がある可能性があります。リリース前に該当箇所の修正（正しい日付返却処理）を推奨します。
- OpenAI SDK 依存
  - API エラー判定で status_code 属性に依存する箇所があるため、将来の SDK 変更（属性名変更等）に注意が必要。
- DuckDB バージョン依存
  - executemany の振る舞いに関してコード内で互換性対策を行っているが、テスト環境で利用する DuckDB のバージョン差異に注意。
- モデル／コスト
  - デフォルトで gpt-4o-mini を利用する設定。実運用ではコスト制御やレートリミットポリシーの検討が必要。
- 時刻取り扱い
  - ニュースウィンドウなどで UTC naive な datetime を利用する設計。タイムゾーン混入に注意して DB の保存・参照は UTC 前提で統一すること。

---

今後の予定（例）
- pipeline の残り実装の完成とユニットテスト追加
- strategy / execution / monitoring モジュールの実装（公開 API に含まれるが未実装箇所がある可能性あり）
- CI による自動テスト・型チェックの導入
- ドキュメント（Usage / デプロイ手順 / 環境変数サンプル）の整備

(以上)