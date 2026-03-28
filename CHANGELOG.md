# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは Keep a Changelog のフォーマットに準拠しています。  
安定性・再現性のため、実装上の設計方針や既知の挙動も併せて記載しています。

なお、以下の変更はコードベースの内容から推測して記載しています。

## [0.1.0] - 2026-03-28

### 追加 (Added)
- パッケージ初期リリース。
  - パッケージ情報:
    - パッケージ名: kabusys
    - バージョン: 0.1.0（src/kabusys/__init__.py）
    - エクスポートモジュール: data, strategy, execution, monitoring（プレースホルダ含む）
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動ロードする仕組みを実装。
  - 自動ロードの探索はパッケージファイル位置から .git / pyproject.toml を辿ってプロジェクトルートを特定（CWD非依存）。
  - .env/.env.local の読み込み優先度: OS 環境変数 > .env > .env.local（.env.local は override=True で上書き）。
  - 読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード停止。
  - .env のパース機能を実装:
    - `export KEY=val` 形式対応。
    - シングル/ダブルクォートを考慮したエスケープ処理。
    - インラインコメント判定（クォート外、直前がスペース/タブの場合のみ # をコメントとする）。
  - 必須環境変数取得ヘルパー `_require` と Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
  - 環境種別・ログレベルのバリデーション（KABUSYS_ENV: development|paper_trading|live、LOG_LEVEL: DEBUG|INFO|...）。

- AI モジュール (src/kabusys/ai/)
  - ニュースセンチメント分析 (news_nlp.py)
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）にバッチ送信して銘柄別スコアを取得。
    - バッチ処理: 最大20銘柄/コール、1銘柄あたり最大10記事・3000文字でトリム。
    - JSON Mode を使った厳格なレスポンス期待と冗長パースのフォールバック（最外側の {} を抽出して復元）。
    - リトライ戦略: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ。
    - レスポンス検証: results 配列・code/score の整合性チェック、未知コードは無視、スコアを ±1.0 にクリップ。
    - 書き込みは部分原子的に実施（該当 code の DELETE → INSERT）して部分失敗時に既存データを保護。
    - テスト容易性: OpenAI 呼び出し関数を patch 可能（_call_openai_api の差し替えを想定）。
    - 公開関数: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
    - ニュース収集ウィンドウ計算 helper: calc_news_window(target_date)（JST 基準で前日 15:00 ～ 当日 08:30 を UTC に変換）。
  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321（225連動型）の 200 日移動平均乖離（重み70%）とニュース LLM センチメント（重み30%）を合成し、市場レジーム（bull/neutral/bear）を日次判定。
    - LLM（gpt-4o-mini）呼び出しは独立実装でモジュール結合を避ける設計。
    - マクロニュース抽出はマクロキーワードリストに基づくフィルタ（最大20件）。
    - API 失敗時は macro_sentiment=0.0 でフェイルセーフ。
    - レジームスコア計算の閾値とスケールを定数化（MA_SCALE, MA_WEIGHT, MACRO_WEIGHT, BULL/BEAR_THRESHOLD 等）。
    - DB への書き込みは冪等操作（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）を実施。
    - 公開関数: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。

- データプラットフォーム周り (src/kabusys/data/)
  - ETL パイプライン (pipeline.py)
    - ETL 実行結果を表す dataclass ETLResult を実装（取得件数・保存件数・品質チェック結果・エラー一覧等）。
    - 差分取得、バックフィル、品質チェックの想定設計を実装（最小日付、lookahead、backfill の定数）。
    - DuckDB 用ユーティリティ（テーブル存在チェック、最大日付取得など）。
  - ETL の公開: data/etl.py で ETLResult を再エクスポート。
  - マーケットカレンダー管理 (calendar_management.py)
    - market_calendar テーブルに基づいた営業日判定（is_trading_day, is_sq_day）。
    - 翌営業日/前営業日取得（next_trading_day, prev_trading_day）、期間内営業日リスト取得（get_trading_days）。
    - DB にデータがない場合は曜日ベース（土日除外）でフォールバックする一貫したロジック。
    - カレンダー更新ジョブ calendar_update_job(conn, lookahead_days) を実装（J-Quants API クライアントと連携して差分取得・保存、バックフィル、健全性チェック）。
    - DuckDB 日付値の扱いと NULL 状態のログ出力を考慮。

- リサーチライブラリ (src/kabusys/research/)
  - factor_research.py
    - モメンタム（1M/3M/6M リターン、200日MA乖離）、ボラティリティ（20日 ATR・相対ATR）、流動性（20日平均売買代金・出来高変化率）、バリュー（PER, ROE）を DuckDB に対する SQL と Python で計算する関数を実装。
    - 関数群: calc_momentum, calc_volatility, calc_value。戻り値は (date, code) を含む dict のリスト。
    - レコード不足時は None を返す設計（安全対策）。
  - feature_exploration.py
    - 将来リターン計算 calc_forward_returns（任意ホライズン、horizons の検証）。
    - IC（Information Coefficient）計算 calc_ic（Spearman の ρ をランクで算出、3件未満は None）。
    - ランク変換ユーティリティ rank（同順位は平均ランク、round で浮動小数の ties を安定化）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median）。
  - research/__init__.py で主要関数を再エクスポート（zscore_normalize を含む）。

- DuckDB を主要なローカルデータストアとして想定し、各モジュールは DuckDB 接続を受け取る形で実装。

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- 読み込み可能な .env フォーマットの堅牢化（クォート・エスケープ・コメント処理）。
- OpenAI API 呼び出し周りでの例外ハンドリングとリトライロジックを整備。サーバーエラー（5xx）とネットワーク系のリトライを区別し、最大試行回数を設定。

### 非推奨 (Deprecated)
- （初期リリースのため該当なし）

### 削除 (Removed)
- （初期リリースのため該当なし）

### セキュリティ (Security)
- 環境変数のロード時に OS 環境変数を保護する仕組みを導入（読み込み時に protected set を使用して上書きを抑止）。
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY で指定する設計。明示的な未設定時には ValueError を発生させるため、誤った公開を防止。

---

## 既知の設計方針・制約（備考）
- ルックアヘッドバイアス防止: ほとんどの処理で datetime.today()/date.today() を直接参照せず、target_date ベースで計算する設計が採用されています（再現性確保）。
- DuckDB バインド/制約: executemany に空リストを渡さないなど DuckDB バージョン固有の注意点に配慮。
- LLM のレスポンスは不安定になり得るため、フェイルセーフ（スコア=0.0 など）で運用継続可能な実装になっています。
- jquants_client（Data モジュール内で利用想定）や Slack 通知等は設定値依存。必要な環境変数を正しく設定すること。

---

今後の予定（今後のリリースで想定）
- strategy / execution / monitoring の具体実装（現時点ではパッケージ公開用の名前空間に留まる）。
- テストカバレッジの強化と CI 統合、ドキュメント化の充実。
- モデルやプロンプトの改善、OpenAI クライアントの抽象化（モックや代替モデル対応）。

もし特に重点的にCHANGELOGへ記載したい変更点や、日付・リリースノートの表記方法（Unreleased 構成など）の希望があれば指定してください。