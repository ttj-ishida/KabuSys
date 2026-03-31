Keep a Changelog
=================

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。
セマンティック バージョニングを採用します。

Unreleased
----------

（今後の変更をここに記載）

[0.1.0] - 2026-03-31
-------------------

初回リリース — 基本機能とコアモジュールを実装しました。

Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - public API エクスポート: data, strategy, execution, monitoring を __all__ で公開。

- 設定管理
  - 環境変数/.env 管理モジュールを追加（kabusys.config）。
  - プロジェクトルート自動探索機能: .git または pyproject.toml を起点に .env を検索して自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサーの強化:
    - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱い対応。
    - 上書き制御 (override) と OS 環境変数保護（protected set）に対応。
  - Settings クラスを提供（必須 env の取得・検証を行うプロパティ群: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）。
  - 環境値の検証: KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL 値検証。

- データプラットフォーム
  - ETL パイプライン基盤（kabusys.data.pipeline）:
    - 差分取得、バックフィル、品質チェックを行う設計を反映。
    - ETL 実行結果を表す dataclass ETLResult を追加（kabusys.data.etl で再エクスポート）。
  - マーケットカレンダー管理（kabusys.data.calendar_management）:
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを実装。
    - calendar_update_job により J-Quants から差分取得して market_calendar を冪等更新する処理を実装。
    - DB にデータがない場合は曜日ベースのフォールバック（週末は休場）を採用。
    - 最大探索日数やバックフィル／健全性チェック等の安全策を導入。

- AI（自然言語処理）モジュール
  - ニュースセンチメント（kabusys.ai.news_nlp）:
    - raw_news / news_symbols を元に銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でバッチ評価して ai_scores テーブルへ書き込む。
    - タイムウィンドウの計算（前日15:00 JST ～ 当日08:30 JST）、記事トリム（最大記事数・文字数制限）、バッチサイズ制御（最大 20 銘柄/コール）。
    - JSON Mode を期待したレスポンス処理、堅牢なレスポンスバリデーション、スコアの ±1.0 クリップ。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。テスト用に _call_openai_api をモック可能。
    - 成功分のみを DELETE → INSERT のトランザクションで置換して書き込むことで部分失敗時に既存データを保護。
  - 市場レジーム判定（kabusys.ai.regime_detector）:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロキーワードフィルタリング、OpenAI 呼び出し（gpt-4o-mini）、リトライ・フォールバック（API 失敗時は macro_sentiment=0.0）、スコア合成と market_regime テーブルへの冪等書き込みを実装。
    - ルックアヘッドバイアス防止の設計（datetime.today() を参照しない、prices_daily は target_date 未満のデータのみ使用）。

- リサーチモジュール（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M）、200日MA乖離、ATR（20日）、流動性指標（20日平均売買代金、出来高比率）、Value（PER, ROE）を DuckDB SQL を用いて計算する関数を追加。
    - データ不足時の戻り値の扱い（None）、結果を (date, code) をキーとする dict のリストで返す仕様。
  - feature_exploration:
    - 将来リターン calc_forward_returns（任意 horizon のサポート、入力検証）。
    - Information Coefficient（calc_ic: スピアマンランク相関）計算。
    - ランク変換ユーティリティ rank、ファクター統計要約 factor_summary を実装。
  - kabusys.research パッケージの __all__ で主要関数を再エクスポート。

- データユーティリティ
  - DuckDB を主要なローカル分析ストアとして利用する設計に沿った SQL 実装。
  - 日付や NULL の扱いに関する慎重な実装（_to_date 等）。

Changed
- （初版のため既存バージョンからの変更は無し。設計上の仕様や安全策を説明に反映。）

Fixed
- フェイルセーフ動作を明確化:
  - AI モジュールで API エラーやレスポンスパース失敗が発生した場合、例外を上げずにロギングしてスコアを 0.0（中立）で継続する実装を採用。
  - 1321 の MA 計算でデータ不足時は中立値（ma200_ratio=1.0）を使用し、警告ログを出力。

Security
- 機密情報の取り扱い:
  - Settings は必須トークンを環境変数から取得し、未設定時は明示的に ValueError を送出して失敗を明確化。
  - .env の自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能（テスト向け）。

Internals / Testing
- OpenAI 呼び出し関数（各モジュールの _call_openai_api）はテストでモック可能な設計になっている（unittest.mock.patch で差し替えを想定）。
- DuckDB executemany による空リストバインドの回避や、transaction（BEGIN/COMMIT/ROLLBACK）周りの厳格な取り扱いにより互換性・堅牢性を向上。

Notes / Known limitations
- 本リリースでは PBR や配当利回りなど一部 Value 指標は未実装。
- OpenAI の利用は gpt-4o-mini および JSON Mode を想定しているため、API 仕様の変更がある場合は影響を受ける可能性あり。
- 一部 DuckDB のバージョン依存（配列バインドの挙動など）を回避するために実装上のワークアラウンドを導入している。

今後の予定（案）
- PBR・配当利回り等バリュー指標の追加実装。
- strategy / execution / monitoring の具体的なアルゴリズムと安全な実行フローの実装。
- テストカバレッジ拡充（OpenAI 呼び出しと DB トランザクションの統合テスト含む）。

---

注: 上記はソースコードの内容とコメントから推測してまとめた初版 CHANGELOG です。実際のリリースノートに反映する際は、リリース日、変更点の粒度や担当者情報などをプロジェクトの運用ルールに合わせて調整してください。