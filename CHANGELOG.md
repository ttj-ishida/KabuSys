CHANGELOG
=========

すべての注目すべき変更履歴を記録します。
このファイルは「Keep a Changelog」仕様に準拠しています。

フォーマット:
- 新機能は Added
- 変更は Changed
- バグ修正は Fixed
- 後方互換性を破る変更は Removed に記載

Unreleased
----------

（現在のリリースは v0.1.0 のため、未リリース変更はありません）

0.1.0 - 2026-03-29
-----------------

Added
- 初回リリース: kabusys パッケージ v0.1.0 を追加。
  - パッケージ構成:
    - kabusys.config: 環境変数 / .env 管理（自動読み込み、.env.local 上書き、OS 環境保護、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読込無効化）。
      - .env パーサーは export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメント取り扱い等に対応。
      - 必須キー取得用の _require と、KABUSYS_ENV / LOG_LEVEL のバリデーションを提供。
      - Slack, J-Quants, kabu API などの設定プロパティを用意（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, KABU_API_PASSWORD）。
      - データベースパス (DUCKDB_PATH, SQLITE_PATH) のデフォルトを提供。
    - kabusys.ai:
      - news_nlp.score_news:
        - raw_news / news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出・ai_scores テーブルへ保存。
        - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）、バッチサイズ、記事数・文字数トリム、JSON Mode を用いた堅牢なレスポンス処理。
        - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、失敗時は該当チャンクをスキップして処理継続。
        - API 呼び出しの抽象化（_call_openai_api）によりユニットテストでの差し替えを容易化。
      - regime_detector.score_regime:
        - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（LLM で評価、重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
        - LLM 呼び出し失敗時は macro_sentiment = 0.0 のフェイルセーフ、API キー注入可能、応答の JSON パースとリトライロジックを実装。
        - レジーム結果を market_regime テーブルへ冪等に保存（BEGIN / DELETE / INSERT / COMMIT）。
    - kabusys.research:
      - factor_research: calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials のみを参照）。
        - モメンタム（1M/3M/6M、MA200乖離）、ATR（20日）、流動性指標、PER/ROE 等を計算。
        - データ不足時は None を返す設計。
      - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank を実装。
        - 将来リターン計算（任意ホライズン）、スピアマン IC（ランク相関）、統計サマリーなどを提供。
        - pandas 等の外部依存なしで標準ライブラリと SQL（DuckDB）で実装。
    - kabusys.data:
      - calendar_management:
        - market_calendar を用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。
        - カレンダー無しや未登録日のフォールバック（曜日ベース）を一貫して扱う。
        - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等に更新。バックフィル／健全性チェックを実装。
      - pipeline / etl:
        - ETLResult データクラスを導入（取得数・保存数・品質問題・エラーの集約）。
        - 差分取得、backfill、品質チェックを想定したユーティリティ関数群を提供。
      - jquants_client と連携する想定の実装（fetch/save の呼び出し）。
    - パッケージ初期化: kabusys.__init__ に __version__ = "0.1.0"、主要サブパッケージを __all__ で公開。

Changed
- 設計方針の明確化:
  - すべての分析/計算モジュールは datetime.today() / date.today() を内部で参照しない（外部から target_date を注入）ことでルックアヘッドバイアスを防止。
  - DB 書き込みは可能な限り冪等に（DELETE → INSERT、ON CONFLICT 相当の挙動を想定）し、部分失敗時に既存データを保護。
  - DuckDB 0.10 の制約（executemany に空リストを渡せない等）への対応を実装。
  - OpenAI 呼び出しで JSON mode を利用し、レスポンスの前後ノイズや非 JSON 応答を復元するロバストなパーシングを実装。

Fixed
- フェイルセーフ／ロバストネス向上:
  - OpenAI の各種例外（RateLimitError, APIConnectionError, APITimeoutError, APIError）に対する分類とリトライ／フォールバック挙動を整理。
  - API レスポンスパース失敗時は例外伝播せずデフォルト値（0.0）やスキップで処理を継続することで ETL/バッチ処理の安定性を確保。
  - DuckDB 書込み失敗時に ROLLBACK を試み、ROLLBACK 自体が失敗した場合は警告ログを出すように改善。

Security
- 環境変数管理:
  - OS 環境変数を保護する機構を導入（.env 読み込み時に既存 OS 環境変数を上書きしない / .env.local で明示的に上書き可能）。
  - API キーの取得は引数注入を許容し、テスト時や CI での差し替えを容易に。

Notes / Implementation details
- OpenAI: gpt-4o-mini を想定し JSON Mode を利用。モデル・リトライパラメータは定数化されているため将来的に調整可能。
- マクロキーワードやウィンドウサイズ、BA TCH サイズ、スコアクリップ範囲、しきい値（bull/bear）などはモジュール定数として分離。
- 単体テストのために _call_openai_api の差し替え（unittest.mock.patch）や api_key 引数注入が可能。
- ロギングを適切に挿入し、警告・情報・デバッグ出力で運用時のトラブルシュートを支援。

今後の予定（提案）
- ai モジュールのモデル切替／パラメータ最適化 UI を追加。
- データ品質チェックモジュールの詳細実装と、それに基づく自動アラート（Slack 通知など）。
- monitoring / execution サブパッケージの実装・ドキュメント整備（現在 __all__ に含まれるがソースは本稿範囲外）。

お問い合わせ・貢献
- バグ報告・機能要望は issue を立ててください。
- コントリビュートは PR を歓迎します。README / CONTRIBUTING を参照してください。