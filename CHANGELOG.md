Keep a Changelog — 変更履歴
すべての変更は https://keepachangelog.com/ja/ の規約に準拠して記載しています。

Unreleased
---------


[0.1.0] - 2026-03-31
-------------------
Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開情報:
    - __version__ = "0.1.0"
    - パブリックモジュール: data, strategy, execution, monitoring

- 環境設定・ロード機能（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読込（プロジェクトルートを .git / pyproject.toml で探索）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーの強化:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応
    - クォートなしでのインラインコメント（#）の扱いの改善
  - 設定値アクセス用 Settings クラス実装（必須キーは _require() で検証）。
  - 代表的な必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - ログレベル / 実行環境（development / paper_trading / live）などのバリデーションを実装。

- AI モジュール（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメント（ai_scores）を作成。
    - タイムウィンドウ計算（JST 基準 -> DB は UTC 想定）。
    - 銘柄ごとに最新記事をトリム（最大記事数・文字数制限）。
    - バッチ処理（最大 20 銘柄/コール）・JSON Mode 出力を期待。
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx を指数バックオフでリトライ。
    - レスポンスの厳密なバリデーション実装（results 配列・code/score 等）。
    - スコアは ±1.0 にクリップ。
    - DuckDB の executemany に関する互換性考慮（空リストは送らない）。
    - テスト容易性: _call_openai_api を patch して差し替え可能。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で regime を決定（bull / neutral / bear）。
    - マクロニュースは news_nlp の window 計算を利用。
    - OpenAI 呼び出しは独立実装（モジュール結合を避ける設計）。
    - API エラー時は macro_sentiment=0.0 のフェイルセーフ。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。

- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar テーブルを基に営業日判定・前後営業日探索・期間内営業日取得・SQ判定などのユーティリティを提供。
    - データがない場合は曜日（土日）のフォールバックを採用。
    - calendar_update_job により J-Quants API からの差分取得 → 保存処理を実装（バックフィル・健全性チェックを含む）。
  - ETL / パイプライン（pipeline, etl）
    - ETLResult データクラスを定義し、ETL 実行結果の集約を提供。
    - 差分更新、バックフィル、品質チェック（quality モジュール経由）に基づく設計方針を実装。
    - DuckDB 互換性のためのユーティリティ関数（テーブル存在チェック・最大日付取得など）を提供。
  - jquants_client 等クライアント類は別モジュール（想定）として利用。

- リサーチ / ファクター（kabusys.research）
  - ファクター計算群（factor_research）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を用いて PER / ROE を計算（PBR 等は未実装）。
    - 各関数は DuckDB SQL を利用し、(date, code) ベースの辞書リストを返す。
  - 特徴量探索（feature_exploration）
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算（最低 3 レコード必要）。
    - rank / factor_summary: ランク変換、統計サマリー（count/mean/std/min/max/median）を実装。
  - kabusys.data.stats の zscore_normalize を再エクスポート。

Changed
- 設計方針として、全ての時刻依存処理は datetime.today()/date.today() を直接参照しない設計を採用（ルックアヘッドバイアス防止）。
- DuckDB の挙動差（executemany の空リスト不可、リストバインドの不安定さ）へのワークアラウンドを盛り込んだ実装。

Fixed / Safe defaults
- OpenAI API 呼び出しでの例外処理を強化:
  - RateLimitError / APIConnectionError / APITimeoutError / APIError の扱いを明確化し、リトライやフォールバック（0.0）を実装。
  - レスポンスパース失敗時は例外を投げずに警告ログを出してフェイルセーフ動作。
- データ不足時の安全策:
  - _calc_ma200_ratio: データ不足または非存在時に中立値 ma200_ratio=1.0 を返し、警告ログを出力。
  - score_news / score_regime: LLM 未呼び出しや失敗時に 0.0 を用いるフェイルセーフ。
- DB 書き込み時のトランザクション保護:
  - BEGIN / DELETE / INSERT / COMMIT を用い、失敗時は ROLLBACK を行いログ出力。

Notes / Implementation details
- OpenAI クライアントは openai.OpenAI を利用（model: gpt-4o-mini、JSON Mode を期待）。
- テスト容易性のため、外部 API 呼び出しを差し替え可能な内部関数（_call_openai_api 等）を用意。
- 時刻窓やタイムゾーン取り扱いは明示（ニュースウィンドウは JST 基準で計算して DB 比較は UTC naive datetime を使用）。
- 多くのモジュールで DuckDB 接続を引数として受け取り、純粋なデータ処理ロジックを実装（本番発注等の副作用なし）。

Known limitations / TODO（今後想定される改善点）
- 一部指標（PBR、配当利回りなど）は現バージョンで未実装。
- OpenAI のモデル/API仕様の変化に対する依存を減らすための抽象化やリクエスト最適化の余地あり。
- カレンダーデータの初期取得 / J-Quants クライアント間のエラー処理強化や観測性向上（メトリクス等）。
- 大規模データ処理におけるパフォーマンスチューニング（バッチサイズ最適化等）。

署名
- この CHANGELOG は提示されたソースコードからの推測に基づいて作成しています。実装の意図・外部モジュールの仕様・運用ルール等により差異が生じる可能性があります。