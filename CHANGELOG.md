# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従っています。  

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-31

初回リリース — 日本株自動売買システムのコアライブラリを実装しました。  
主にデータ取得・ETL、マーケットカレンダー管理、リサーチ（ファクター計算）、およびAIを用いたニュース解析・市場レジーム判定の機能を提供します。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を設定。
  - __all__ に data / strategy / execution / monitoring を公開（将来的モジュール構成を想定）。

- 設定・環境変数管理 (src/kabusys/config.py)
  - Settings クラスを提供し、環境変数経由で各種設定を取得（J-Quants / kabu API / Slack / DB パス / 環境フラグ等）。
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサーは export 構文、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント処理に対応。
  - 必須環境変数未設定時に明示的なエラーを返す _require 関数。
  - env 値・log level の検証（許容値チェック）と利便性プロパティ（is_live / is_paper / is_dev）。

- AI モジュール (src/kabusys/ai)
  - ニュースNLP (src/kabusys/ai/news_nlp.py)
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols を集約し OpenAI（gpt-4o-mini）にバッチ送信して銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込み。
    - タイムウィンドウ計算（JST 基準）を提供する calc_news_window。
    - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたりの最大記事数・最大文字数トリム、JSON Mode のレスポンス検証とスコアクリップ（±1.0）。
    - 429 / ネットワーク断 / タイムアウト / サーバー5xx に対するエクスポネンシャルバックオフでのリトライ実装。
    - レスポンスの堅牢なパース・バリデーション（余分なテキストの除去や不正スコアの除外）。
    - DuckDB 互換性を考慮したトランザクション（DELETE → INSERT）と executemany の空リスト回避。
    - テスト容易性のため API 呼び出し関数をパッチ差し替え可能（_call_openai_api をモジュール内で定義）。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を組合せ、市場レジーム（bull/neutral/bear）を算出して market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出のためのキーワード集合と最大記事数制限。
    - OpenAI 呼び出しは JSON モードで行い、再試行ロジック・フェイルセーフ（API 失敗時 macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス防止: prices_daily / raw_news のクエリで target_date 未満のデータのみを利用し、内部で datetime.today() を参照しない設計。
    - トランザクションでの書き込み失敗時は ROLLBACK を行い上位へ例外伝播するよう実装（ROLLBACK 失敗時は警告ログ）。

- データプラットフォーム (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルに基づく営業日判定 API: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - DB データがない/未登録日の場合は曜日ベース（土日）でフォールバックする一貫した挙動。
    - calendar_update_job により J-Quants API から差分取得して market_calendar を冪等更新（バックフィル・健全性チェックあり）。
    - 最大探索日数・先読み/バックフィル日数等の安全パラメータを設定。

  - ETL / パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult dataclass を定義し、ETL 実行の取得件数・保存件数・品質問題・エラー概要を集約して監査やログに利用可能に。
    - 差分更新、バックフィル、品質チェックを想定した設計方針を実装（関数群はパイプライン実装の基盤を提供）。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得など。

- リサーチ (src/kabusys/research)
  - factor_research.py
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev の計算。データ不足時の None ハンドリング。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率の計算。true_range の NULL 伝播制御。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS 未備の場合は None）。
    - DuckDB による SQL ベース実装、ルックアヘッド回避。

  - feature_exploration.py
    - calc_forward_returns: 各ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得する汎用実装。
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算。レコード不足は None。
    - rank: 同順位処理（平均ランク）を行うランク関数（丸めによる ties 検出対策あり）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで算出する統計サマリー。

- その他
  - OpenAI SDK との統合は gpt-4o-mini をデフォルトモデルに採用。
  - ロギングを多用し、処理の進捗やフォールバック・警告を明確に記録。
  - 多くの箇所でルックアヘッドバイアス対策（target_date 未満のみ参照、datetime.today() を直接参照しない設計）。

### 改良・堅牢化 (Changed / Fixed)
- DuckDB 互換性を意識した実装:
  - executemany に空リストを渡さないガード、list バインドの不安定性回避のため個別 DELETE を実行する実装など。
- OpenAI 呼び出しの堅牢化:
  - レート制限・接続エラー・タイムアウト・サーバーエラー（5xx）に対する再試行ロジックを実装し、非致命的失敗はフェイルセーフ（スコア=0 や該当銘柄スキップ）で継続するようにした。
  - レスポンス JSON パースの回復処理（余計な前後テキストの除去）を追加。
- DB 書き込み: トランザクションでの冪等保存（DELETE → INSERT パターン）と失敗時のロールバック処理を追加し、部分失敗時に既存データを不必要に削除しないよう設計。

### 既知の制限 (Known issues)
- strategy / execution / monitoring の実装はパッケージ公開面で名前空間に含まれるが、今回のスナップショットでは個別モジュール実装が限定的または別途実装を想定している箇所があります。
- 一部の内部関数やモジュール（例: data.jquants_client の具体的実装）は外部依存（J-Quants クライアント）に依存するため、本体だけでは API 呼び出しは行えません。環境変数や外部クライアントの注入が必要です。
- カレンダー / ETL の一部関数は外部 API（J-Quants）に依存し、API レスポンスやアクセス権により動作が制限されます。

---

注意: 上記は提供されたソースコードの内容から推測して作成した変更履歴です。現実のリリース履歴やコミット履歴と差異がある可能性があります。必要であれば特定機能ごとに詳細なリリースノート（例: 各関数の戻り値の形式、ログメッセージ、例外仕様）を追加します。