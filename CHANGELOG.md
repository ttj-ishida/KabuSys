Keep a Changelog
=================
すべての変更は https://keep-a-changelog.com/ の形式に準拠して記載しています。

フォーマット: 変更は「Added / Changed / Fixed / Deprecated / Removed / Security」のカテゴリに分類しています。

Unreleased
----------
（現時点のコードベースは初期リリース相当のため、Unreleased に保留中の項目はありません）

0.1.0 - 2026-03-26
-----------------

Added
- パッケージ基盤を追加
  - kabusys パッケージの公開 API を定義（src/kabusys/__init__.py）。バージョンは 0.1.0、初期モジュール群を __all__ で公開: data, strategy, execution, monitoring。

- 環境設定管理
  - 高機能な .env ローダーを実装（src/kabusys/config.py）。
    - プロジェクトルートを __file__ を起点に .git または pyproject.toml から自動検出。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
    - export KEY=val 形式・シングル/ダブルクォート・エスケープ・インラインコメントを考慮して行単位でパース。
    - 既存 OS 環境変数を保護する protected 機構を搭載（.env の上書きを制御）。
  - Settings クラスを提供（必須環境変数取得用の _require を含む）。
    - J-Quants / kabuAPI / Slack / DB パス等の設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH 等）。
    - KABUSYS_ENV と LOG_LEVEL のバリデーション（有効な値セットをチェック）。
    - is_live / is_paper / is_dev のヘルパーを追加。

- AI モジュール（OpenAI 統合）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信してセンチメントスコアを生成。
    - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - バッチング（最大 20 銘柄 / チャンク）、記事数・文字数上限でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - 再試行（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実装、失敗時は部分スキップして継続（フェイルセーフ）。
    - レスポンス検証ロジック（JSON 抽出、results 配列検証、コード一致チェック、スコアの数値・有限性チェック、±1.0 クリップ）。
    - 書き込みは冪等性を考慮（対象コードのみ DELETE → INSERT）して部分失敗時に既存データを保護。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で market_regime を判定・保存。
    - マクロキーワードで raw_news をフィルタしてタイトルリストを作成し、OpenAI（gpt-4o-mini）で JSON 出力（{"macro_sentiment": ...}）を期待。
    - API 呼び出し失敗時は macro_sentiment=0.0 へフォールバック（警告ログ）。合成スコアをクリップしてラベル (bull/neutral/bear) を決定。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等操作、失敗時は ROLLBACK を試行して例外を伝播。

- Research モジュール（src/kabusys/research/）
  - factor_research.py: ファクター計算関数を追加
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA 乖離）を DuckDB SQL で実装。データ不足時の None ハンドリング。
    - calc_volatility: 20 日 ATR（true range 処理）、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算。EPS が 0/欠損のケースを考慮。
  - feature_exploration.py: 解析ユーティリティを追加
    - calc_forward_returns: 指定ホライズンの将来リターン（LEAD を用いた一括クエリで実装、入力検証あり）。
    - calc_ic: スピアマンのランク相関（IC）を実装（None / 非有限値除外、最小有効件数チェック）。
    - rank: 同順位は平均ランクにするランク化実装（丸めで ties の検出を安定化）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを算出。
  - research パッケージ初期エクスポートを定義（zscore_normalize 等も再エクスポート）。

- Data モジュール（src/kabusys/data/）
  - calendar_management.py: JPX カレンダー管理と営業日ロジックを追加
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - market_calendar が未取得の場合は曜日ベース（平日を営業日）でフォールバック。
    - DB 登録値を優先しつつ未登録日は曜日フォールバックで一貫した結果を返す設計。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新する夜間ジョブ実装（バックフィル、健全性チェック、API エラーハンドリング）。
  - pipeline.py: ETL パイプライン基盤を追加
    - ETLResult データクラスを提供（取得数 / 保存数 / 品質問題 / エラー集約、has_errors/has_quality_errors プロパティ、辞書変換）。
    - 差分取得・backfill・品質チェック方針を実装方針に反映（jquants_client を利用、idempotent な保存を期待）。
  - etl.py: ETLResult をパブリックに再エクスポート。

Changed
- 設計方針として「datetime.today() / date.today() を参照しない」方針を各所で採用（ルックアヘッドバイアス防止）。target_date を明示的に渡す API に統一。

Fixed
- 各種 API 呼び出しに対するリトライとフェイルセーフ動作を整備（OpenAI API 呼出しの例外ハンドリングとバックオフポリシーを導入）。

Security
- 環境変数・APIキーを settings 経由で必須チェックし、未設定時は ValueError で明確に通知（OPENAI_API_KEY、JQUANTS_REFRESH_TOKEN、SLACK_*、KABU_API_PASSWORD 等）。

Notes / Implementation details
- OpenAI 呼び出しは gpt-4o-mini を想定し、JSON Mode（response_format={"type":"json_object"}）での利用を前提とした実装。ただしレスポンスパース失敗に備えた耐障害性ロジックを含む。
- News NLP と Regime Detector で OpenAI 呼び出しヘルパー関数は別々に実装し、モジュール間でプライベート関数を共有しない設計（結合度を下げる）。
- DuckDB をクエリ主体で多用し、外部解析ライブラリ（pandas 等）に依存しない実装を目指している。
- DB 書き込みは可能な限り冪等に（DELETE → INSERT / ON CONFLICT を想定）し、部分失敗時のデータ保護を優先している。
- カレンダー周りや ETL のいくつかのしきい値（バッファ日数や最大探索日数）は定数化され、ログで健全性チェックを実施する設計。

既知の制限 / TODO（今後の改善候補）
- ai/news_nlp のスコアリングは現在 sentiment_score と ai_score を同値で保存しているが、将来的に別処理に分離する余地あり。
- 一部の DuckDB バインド（list を一括バインドする手法）はバージョン依存のため executemany を用いる等の互換性対策が残っている。
- strategy / execution / monitoring パッケージは公開されているが、本リリースでの実装詳細は限定的（今後の実装拡張を予定）。

作者と連絡
- リポジトリ内のコード（docstring）に記載された設計方針・使用法に従ってください。
- 環境変数の例は .env.example を参照してセットアップしてください。

（以降のリリースでは各機能の拡張・バグ修正・API 変更点を詳細に記載します）