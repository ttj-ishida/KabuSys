Keep a Changelog
================

すべての重要な変更点をこのファイルで管理します。これは "Keep a Changelog" のガイドラインに準拠します。
日付はリリース日を示します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-31
--------------------

Added
- 初期リリース。日本株自動売買プラットフォーム "KabuSys" のコア機能を追加。
  - パッケージ公開:
    - パッケージ名: kabusys
    - バージョン: 0.1.0
    - パッケージトップでの公開モジュール: data, strategy, execution, monitoring（将来的な拡張を想定）
- 設定 / 環境変数管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途）。
  - .env パーサの実装: コメント、export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ等に対応。
  - OS 環境変数を上書きしない既定動作と、.env.local による上書き（override）をサポート。保護対象キーセットを保持して上書きを制御。
  - Settings クラスを提供し、J-Quants・kabu API・Slack・DBパス・監視閾値・環境種別（development/paper_trading/live）・ログレベル等のプロパティを環境変数から安全に取得。
  - 必須環境変数不足時には ValueError を送出。
- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約し、銘柄ごとにニュースを連結して OpenAI (gpt-4o-mini) にバッチ送信してセンチメント（-1.0〜1.0）を取得。
    - チャンク処理（最大 20 銘柄/コール）、記事数・文字数トリム、JSON Mode のレスポンス検証、スコアの ±1.0 クリップを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライの実装。API 失敗時はそのチャンクをスキップして処理継続（フェイルセーフ）。
    - レスポンスパースの堅牢化（JSON モードでも前後余分なテキストが混ざるケースの復元処理）。
    - DuckDB へは部分置換（DELETE → INSERT）で冪等書き込み。空パラメータを事前チェックして DuckDB executemany の制約に対応。
    - テストしやすいように _call_openai_api の差し替え（patch）が可能。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは news_nlp.calc_news_window に基づくウィンドウでフィルタし、OpenAI により JSON 出力の macro_sentiment を取得。
    - OpenAI 呼び出しに対するリトライ（429/ネットワーク/タイムアウト/5xx）とフェイルセーフ（失敗時 macro_sentiment=0.0）。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）と ROLLBACK の取り扱い。
    - 設計指針としてルックアヘッドバイアス防止（datetime.today()/date.today() を参照しない / date < target_date 条件）を採用。
- データプラットフォーム (kabusys.data)
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間バッチ更新 job（calendar_update_job）を実装。J-Quants からの差分取得と market_calendar テーブルへの冪等保存を実現。
    - 営業日判定 API: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。DB 登録値優先・未登録日は曜日（平日）でフォールバック。
    - 探索範囲上限と健全性チェック（最大探索日数・未来日付の異常検出）、およびバックフィルの実装。
  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを追加し、ETL 実行結果（取得数・保存数・品質問題・エラー等）を表現。
    - 差分更新・バックフィル・品質チェックの方針を反映した内部ユーティリティ実装スケルトン（テーブル存在チェック・最大日付取得等）。
    - jquants_client / quality モジュールとの連携点を想定（fetch/save/品質検査）。
  - jquants_client 参照箇所を想定し、DataPlatform の設計に準拠した処理を実装（外部 API 呼び出し箇所は抽象化）。
- リサーチ / ファクター (kabusys.research)
  - factor_research:
    - モメンタム、ボラティリティ、バリュー（PER, ROE）等のファクター計算関数を追加。
    - DuckDB SQL を用いた実装で、prices_daily / raw_financials テーブルのみを参照。出力は (date, code) をキーとする辞書リスト。
    - 各関数はデータ不足時に None を返すなど堅牢な振る舞いを実装。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（Spearman の ρ）計算（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を追加。外部依存を排して標準ライブラリで実装。
  - research パッケージ __all__ 経由で主要関数を再エクスポート。
- 共通 / 実装方針
  - DuckDB を中心とした SQL ベースのデータ処理を採用。
  - ルックアヘッドバイアス防止のため、日次処理では明示的な target_date パラメータを用いる設計。
  - API 呼び出し失敗時はフェイルセーフ（例: スコア 0.0、チャンクスキップ）で処理を継続する方針。
  - 重要箇所にログ出力と警告を実装して運用観察を容易にする。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / 運用メモ
- OpenAI API を利用する機能（news_nlp, regime_detector）は環境変数 OPENAI_API_KEY または関数引数で API キーを受け取る。未設定の場合は ValueError を送出するため、バッチ実行前にキー設定が必要。
- .env の自動読み込みはプロジェクトルートを基準に行うため、パッケージ配布後の実行環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して明示的に環境を管理することを推奨。
- DuckDB executemany に関する互換性制約に配慮して実装されている（空リストバインド禁止への対応）。
- 将来的に strategy / execution / monitoring パッケージの実装拡張を予定。

作者・貢献者
- KabuSys 開発チーム

-----