Keep a Changelog
=================

すべての変更は https://keepachangelog.com/ja/ に準拠して記載しています。

0.1.0 - 2026-04-02
-----------------

導入（Added）
- 初回公開: KabuSys 日本株自動売買／データ処理ライブラリのベース実装を追加しました。
  主な機能は以下の通りです。

- パッケージ初期化
  - src/kabusys/__init__.py にてバージョンを "0.1.0" として公開。主要サブパッケージ（data, research, ai, execution, monitoring 等）を __all__ で列挙。

- 環境変数・設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を追加（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を用いて自動ロードを無効化可能。
  - .env パーサ実装の強化:
    - export KEY=val 形式対応
    - シングル／ダブルクォート内のバックスラッシュエスケープ対応
    - コメント処理（クォートあり／なしそれぞれの挙動を区別）
  - .env.local を .env より優先して上書き（OS 環境変数は保護）。
  - Settings クラスを公開（settings インスタンス）:
    - J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / システム環境変数等をプロパティで取得
    - バリデーション: KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL 値チェック
    - Path 型の展開（~ の展開）、数値閾値の float 変換等

- AI（OpenAI）統合（src/kabusys/ai/*）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄別にニュースを集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメントを取得。
    - タイムウィンドウ計算 calc_news_window（JST 前日15:00〜当日08:30 を UTC に変換）を提供。
    - バッチ処理: 最大 _BATCH_SIZE=20 銘柄ごとに処理、1銘柄あたり記事上限・文字数上限でトリム。
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフで再試行。
    - レスポンスの堅牢なバリデーション: JSON モードでも前後テキストが混入するケースに対応して "{}" 部分を抽出してパース、results フィールド検証、コード正規化、スコア数値化・有限性チェック、±1.0 でクリップ。
    - DuckDB への書き込みは部分的失敗を避けるため、取得した銘柄のみを DELETE → INSERT（冪等）。DuckDB executemany の空リスト制約に対応。
    - score_news API を公開し、成功時に書き込んだ銘柄数を返す。API キーは引数または環境変数 OPENAI_API_KEY で解決。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して 'bull' / 'neutral' / 'bear' を日次判定。
    - MA 計算は target_date 未満のみを使用してルックアヘッドを防止。
    - マクロニュースは raw_news からマクロキーワードでフィルタし、最大件数を LLM に送る。
    - OpenAI 呼び出しは独立実装で、リトライや 5xx 判定、JSON パース失敗時はマクロセンチメントを 0.0 にフォールバックするフェイルセーフ実装。
    - 判定結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。score_regime API を公開。
  - テスト容易性向上: OpenAI 呼び出し関数を patch で差し替えられる設計。

- データ基盤（src/kabusys/data/*）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar をベースに営業日判定／前後営業日、期間内営業日列挙、SQ 日判定などのユーティリティを実装。
    - DB データが存在する場合は DB 値優先、未登録日は曜日ベースのフォールバック（週末は非営業日）を行い、DB がまばらでも一貫した結果を返す設計。
    - calendar_update_job を提供し、J-Quants から差分取得して market_calendar を冪等更新。バックフィル・健全性チェック付き。
  - ETL パイプラインインターフェース（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）
    - ETLResult データクラスで ETL 実行の集約結果（取得数、保存数、品質問題、エラー）を表現。to_dict により品質問題を辞書化して監査ログに利用可能。
    - 差分更新／バックフィル／品質チェックの方針に沿った ETL 実装基盤（jquants_client と quality モジュールとの連携想定）。DuckDB の存在チェックなどのユーティリティあり。
    - etl.py は pipeline.ETLResult を再エクスポート。

- リサーチ（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）を計算する関数を実装。
    - DuckDB 上の prices_daily / raw_financials を使用し、外部 API へはアクセスしない設計。
    - データ不足時は None を返すことで下流での扱いを明確化。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）：複数ホライズンを一度に取得する SQL、horizons 引数の検証あり。
    - IC（Information Coefficient）計算（calc_ic）：スピアマンの順位相関を内製で実装（外部依存なし）。有効レコード数が 3 未満の場合は None。
    - ランク関数（rank）: 同順位は平均ランクにし、丸めで ties 判定の安定化を行う。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出。
    - research パッケージの __init__ で主要関数群を再エクスポート。

- 実装上・設計上の重要な注意点（ドキュメント化された振る舞い）
  - ルックアヘッドバイアス防止: date.today()/datetime.today() を参照しない設計（関数は target_date を受け取る）。
  - フェイルセーフ: 外部 API（OpenAI / J-Quants）失敗時は致命的に失敗させず、既定値やスキップで継続する実装方針（ログ出力で通知）。
  - IDempotency（冪等性）を重視した DB 書き込みパターン（DELETE → INSERT、ON CONFLICT の使用想定）。
  - DuckDB 互換性への配慮（executemany に空配列を渡さない、日付型取り扱い等）。
  - ロギングを広く導入：処理状況・警告・例外は適切にログ出力。

変更（Changed）
- 初回リリースのため該当なし。

修正（Fixed）
- 初回リリースのため該当なし。

既知の制約・TODO
- jquants_client や quality など外部モジュールとの連携部分は、実際の API クライアント実装に依存するため環境に応じた接続設定が必要。
- OpenAI を利用する機能は API キー（OPENAI_API_KEY）が必須。テスト時は _call_openai_api をモック可能。
- pipeline モジュールの末尾に一部実装が未完（ソース切断の可能性）を確認してください（パッケージを使用する環境では該当箇所の完全実装が必要）。

開発者向けメモ
- テスト容易性:
  - OpenAI コールは各モジュール内の _call_openai_api を patch して差し替え可能。
  - 環境変数自動読み込みを KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑止できるため、ユニットテスト中に環境を固定しやすい。
- ログレベルや環境は settings から取得して一貫して使用してください。

--- 

（本 CHANGELOG は、コードベースの内容から推測して作成しています。実際のリリースノートは運用方針に合わせて編集してください。）