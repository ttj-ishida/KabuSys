# CHANGELOG.md

全ての注記は Keep a Changelog の形式に従います。  
このファイルはコードベースから推測して作成した変更履歴です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買・データプラットフォームのコア機能を提供する最小実装を追加。

### Added
- パッケージの基本情報
  - パッケージ名: kabusys、バージョン `0.1.0` を設定（src/kabusys/__init__.py）。
  - パッケージ公開 API として data, strategy, execution, monitoring をエクスポート。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動ロードする仕組みを実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索して決定（カレントワーキングディレクトリに依存しない）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - .env パーサーは `export KEY=val` 形式、クォート・バックスラッシュエスケープ、行末コメント処理をサポート。
    - 既存 OS 環境変数を保護するための protected キーセットに対応して上書き制御を実装。
  - Settings クラスを提供し、主要設定値をプロパティ経由で取得:
    - J-Quants / kabuステーション / Slack / DB パス等の必須・デフォルト設定を含む。
    - `KABUSYS_ENV` と `LOG_LEVEL` の値検証（有効値チェック）を実装。
    - パスは Path オブジェクトで返却（duckdb/sqlite のデフォルトパスあり）。

- AI (自然言語処理) モジュール (src/kabusys/ai/)
  - news_nlp.py
    - raw_news / news_symbols を元に銘柄別にニュースを集約し、OpenAI (gpt-4o-mini) を用いて銘柄毎にセンチメントを算出。
    - タイムウィンドウの計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して扱う）。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたり記事数と文字数上限によるトリミング。
    - JSON mode を使った厳密なレスポンス期待と、レスポンスの堅牢なバリデーション実装。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ。
    - API 失敗時はフェイルセーフ（該当チャンクはスキップ、最終的に取得できた銘柄のみ ai_scores に書き込み）。
    - DuckDB 互換性考慮（executemany 空リスト回避）やトランザクション処理（DELETE → INSERT）を実装。
    - 公開関数: score_news(conn, target_date, api_key=None)。
  - regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロセンチメントは news_nlp の記事抽出ロジックを利用し、OpenAI に JSON 出力を要求して数値化。
    - API 呼び出し失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ実装。
    - レジーム結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時に ROLLBACK の試行とログ）。
    - 公開関数: score_regime(conn, target_date, api_key=None)。

- Research（因子・特徴量）モジュール (src/kabusys/research/)
  - factor_research.py
    - Momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を計算する calc_momentum。
    - Volatility / Liquidity: 20 日 ATR（atr_20）・相対 ATR（atr_pct）・20 日平均売買代金・出来高比率を計算する calc_volatility。
    - Value: EPS/ROE など raw_financials から取得して PER/ROE を算出する calc_value。
    - DuckDB の SQL ウィンドウ関数を活用し、欠損やデータ不足に対して None を返す堅牢な実装。
  - feature_exploration.py
    - 将来リターン計算 calc_forward_returns（任意ホライズン、入力検証あり）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンのランク相関、必要レコード数チェック）。
    - ランク化ユーティリティ rank（同順位は平均ランク処理）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median）。
  - 研究用のユーティリティをまとめて再エクスポート（__init__.py）。

- Data（データ取得・管理）モジュール (src/kabusys/data/)
  - calendar_management.py
    - JPX マーケットカレンダー管理（market_calendar）と営業日判定ユーティリティ:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days。
    - 市場カレンダーが未取得の場合は曜日ベース（土日を非営業日）でフォールバックする一貫した挙動。
    - 夜間バッチ calendar_update_job による J-Quants からの差分取得と保存（バックフィル・健全性チェックを含む）。
  - pipeline.py / ETLResult
    - ETLResult データクラスを定義し、ETL の実行結果（取得数・保存数・品質チェック結果・エラー）を表現可能に。
    - ETL モジュールの内部ユーティリティ（テーブル存在チェック、最大日付取得、market calendar 関連ヘルパー）。
  - etl.py で pipeline.ETLResult を再エクスポート。

### Security
- 環境変数の扱いで OS 環境変数を保護する仕組みを導入（.env の上書きを保護）。
- OpenAI API キー・外部サービスのキーは Settings 経由で必須チェックを行い、未設定時は ValueError を発生させる。

### Design / Implementation Notes
- ルックアヘッドバイアス回避:
  - AI/スコアリング・ファクター・ETL などのコア処理は内部で datetime.today()/date.today() を直接参照しない。target_date を明示的に受け取る設計。
  - DB クエリは date < target_date または date BETWEEN 範囲など、未来のデータを参照しないように配慮。
- OpenAI 呼び出し:
  - gpt-4o-mini を想定した JSON Mode を使用し、429/ネットワーク/5xx に対してリトライ（指数バックオフ）を行う。
  - レスポンスパース/バリデーションに失敗してもシステムは継続する（フェイルセーフ）。
  - モジュール間でテスト容易性を考え、OpenAI 呼び出し関数はモジュール内で抽象化している（unit test 用に patch 可能）。
- DB トランザクション:
  - DuckDB に対する書き込みはトランザクションで行い、失敗時は ROLLBACK を試みログ出力する。
  - executemany に空リストを渡せない DuckDB 互換性の考慮がある（空チェックを追加）。

### Known limitations / TODO
- strategy / execution / monitoring パッケージは本実装ではエクスポート対象に含まれているが、本リリースのソースツリーには詳細な発注ロジックや実行エンジンの実装が含まれていない可能性がある（将来的な追加／拡張箇所）。
- news_nlp の出力や regime_detector のしきい値は現フェーズ固定値（ハードコード）。実運用ではパラメータ化やチューニングが必要。
- raw_financials からの PBR・配当利回りなどは未実装（calc_value の注記参照）。
- テストカバレッジやドキュメント（API 使用例）は今後強化予定。

### Migration notes
- .env 自動読み込みはプロジェクトルート検出に .git または pyproject.toml を使用するため、パッケージ配布後に挙動を変えたくない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定し手動で環境変数をロードすることを推奨。

## 参考
- 実装では J-Quants / kabu ステーション / OpenAI（gpt-4o-mini）を前提とした設計が多数含まれます。実運用時は各 API キーとエンドポイントを環境変数で設定してください（Settings のプロパティを参照）。

----
（この CHANGELOG は提供されたソースコードからの推測に基づいて作成しています。実際のリリースノートはプロジェクト履歴やコミットログに基づいて調整してください。）