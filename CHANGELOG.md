Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトでは、Keep a Changelog の慣習に準拠して変更履歴を管理しています。

[0.1.0] - 2026-03-29
--------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
- 基本パッケージ構成を追加
  - パッケージルート: src/kabusys/__init__.py（バージョン情報、公開 API 指定）
- 環境変数・設定管理（src/kabusys/config.py）
  - .env/.env.local の自動読み込み（プロジェクトルート（.git または pyproject.toml）基準）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
  - .env ファイルの柔軟なパース（export プレフィックス、シングル/ダブルクォート、インラインコメントの取り扱い）
  - Settings クラスで各種必須設定の取得（J-Quants、kabuステーション、Slack、DB パス、環境判定、ログレベル検証等）
  - OS 環境変数を保護する読み込みロジック（.env.local で上書き可能だが OS 環境変数は保護）
- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとのニュースを LLM（gpt-4o-mini）でセンチメント付与
    - バッチ処理（最大20銘柄/チャンク）、記事数・文字数制限（トークン肥大化対策）
    - リトライ戦略（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 構造検証、スコアの ±1.0 クリップ）
    - DuckDB の ai_scores テーブルへ冪等更新（DELETE → INSERT、部分失敗時に他コードの保護）
    - テスト用フック: _call_openai_api を patch で差し替え可能
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）判定
    - OpenAI 呼び出しの専用実装（news_nlp とは別実装でモジュール結合を低減）
    - API 失敗時のフェイルセーフ（macro_sentiment=0.0）とリトライ
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
- データ（src/kabusys/data）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー取得・夜間バッチ更新処理（calendar_update_job）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティ
    - market_calendar が未取得のときの曜日ベースフォールバック、DB 登録値優先の一貫した判定ロジック
    - 最大探索日数やバックフィル、健全性チェックを備えた実装
  - ETL パイプライン基盤（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult dataclass を公開（etl モジュールで再エクスポート）
    - 差分取得、保存、品質チェックを想定したユーティリティ関数群（テーブル存在チェック、最大日付取得など）
    - DataPlatform 設計方針に沿った差分/バックフィルロジック
- リサーチ（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離等の計算
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比等
    - calc_value: raw_financials からの PER/ROE 計算（target_date 以前の最新財務データを使用）
    - DuckDB を用いた SQL ベースの実装（データ参照のみ、外部発注 API へのアクセスなし）
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズンの将来リターン（複数ホライズン対応）
    - calc_ic: スピアマンのランク相関（Information Coefficient）
    - factor_summary: 基本統計量（count/mean/std/min/max/median）
    - rank: 同順位を平均ランクにするランク化ユーティリティ
- 開発者向けの小改善
  - DuckDB の executemany に対する空パラメータ回避（互換性向上）
  - JSON レスポンスの余分テキストを許容して {} 範囲抽出で復元する耐性（LLM の出力雑音対応）
  - 各所で例外を内部で捕捉してフェイルセーフにフォールバックする設計（ETL / AI 呼び出し等）
  - ロギング強化（情報・警告・例外ログ）

Changed
- プロジェクト配布後の環境変数自動ロードを .git / pyproject.toml を基準に探索する実装に変更（カレントワーキングディレクトリに依存しない）
- OpenAI クライアント呼び出しは明示的に api_key を受け取れるようにし、環境変数依存を緩和

Fixed
- DuckDB における部分書き換え処理で executemany に空リストを渡すと失敗する問題を回避（事前に空チェックを実施）
- LLM レスポンスの JSON パース失敗時に例外をそのまま投げないようにして処理を継続（0.0 や空辞書へフォールバック）

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で明示的に指定が必要（未設定時は ValueError を送出）
- .env の自動ロードは OS 環境変数を保護（既存 OS 環境変数は上書きされない）し、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能
- Settings.require により必須環境変数が未設定の場合は早期にエラーとなるため、デプロイ前の環境確認が容易

Notes
- LLM 関連処理は gpt-4o-mini を想定して実装（response_format に JSON mode を利用）
- テスト容易性のため、AI 呼び出し関数（各モジュール内の _call_openai_api）を unittest.mock.patch で差し替え可能
- 日付関連ロジック（ニュースウィンドウ、MA 計算等）は datetime.today()/date.today() を参照しない設計（ルックアヘッドバイアス防止）
- DuckDB に依存した SQL 実装のため、本番運用前に DB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials 等）の整備が必要

未実装 / TODO（今後の作業想定）
- PBR・配当利回りなどのバリュー指標を calc_value に追加
- ai_scores 等への部分的ロールバック・リトライ戦略のさらに詳細な改善
- OpenAI モデル切替・コスト最適化オプションの追加
- 追加の品質チェックルール強化（quality モジュールとの連携拡張）

(End of changelog)