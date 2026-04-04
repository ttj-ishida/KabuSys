# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の慣例に従います。  
このパッケージの初回公開リリースを記録しています。

全般
- リリース日: 2026-04-04
- バージョン: 0.1.0 (初回リリース)

## [0.1.0] - 2026-04-04

### 追加
- パッケージの基本構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込み
    - 自動ロードはプロジェクトルート（.git または pyproject.toml）基準で行い、CWD に依存しない実装
    - 優先順位: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化に対応
  - .env のパース機能を実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）
  - 環境変数上書き時の保護機構（protected keys）
  - settings オブジェクトを提供（J-Quants、kabu API、LINE、DB パス、監視閾値、環境/ログレベル判定など）
  - 必須設定未定義時は _require() が ValueError を送出し明示的に失敗させる

- AI モジュール (src/kabusys/ai)
  - ニュースセンチメント解析（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を元に銘柄別に記事を集約して OpenAI（gpt-4o-mini, JSON mode）へバッチ送信
    - バッチ処理（最大20銘柄／APIコール）・記事数/文字数制限（トリム）によるトークン抑制
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフと再試行ロジック
    - レスポンスの堅牢なバリデーションとスコアの ±1.0 クリップ
    - 書き込みは ai_scores テーブルへ冪等的に実施（該当コードのみ DELETE → INSERT）
    - ルックアヘッドバイアス回避のため datetime.today()/date.today() を参照しないウィンドウ計算（calc_news_window）
    - API キー未設定時は ValueError を送出
    - フェイルセーフ: API 失敗時は当該チャンクをスキップして処理継続
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次レジーム判定（bull/neutral/bear）
    - raw_news からマクロキーワードで記事を抽出し、OpenAI によるマクロセンチメント評価を行う（gpt-4o-mini, JSON mode）
    - API リトライ・エラーハンドリング（バックオフ、5xx の特別扱い）を実装
    - LLM/API 失敗時は macro_sentiment=0.0 をフォールバックし処理継続（フェイルセーフ）
    - market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、例外時は ROLLBACK）
    - ルックアヘッドバイアス防止設計（prices_daily クエリは date < target_date を意識）

- データプラットフォーム関連 (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルを利用した営業日判定 API を提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にカレンダー情報がない場合は土日ベースのフォールバックを使用
    - next/prev/get は DB 登録値を優先し、未登録日は曜日ベースフォールバックで一貫した振る舞い
    - 夜間バッチ job: calendar_update_job により J-Quants から差分取得して market_calendar を冪等更新（バックフィル、健全性チェックあり）
  - ETL パイプライン (src/kabusys/data/pipeline.py / src/kabusys/data/etl.py)
    - ETLResult dataclass を導入（取得件数、保存件数、品質問題、エラー等を集約）
    - 差分更新・バックフィル・品質チェックの設計方針に準拠した下地実装
    - jquants_client を介した取得/保存の呼び出しを想定
    - ETLResult.to_dict() によるシリアライズ（品質問題は辞書化）
    - data/etl で ETLResult を再エクスポート

- リサーチ・ファクター (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum: mom_1m/mom_3m/mom_6m と 200 日 MA 乖離 (ma200_dev) を DuckDB (prices_daily) から計算
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算
    - calc_value: raw_financials から最新財務を取得して PER/ROE を計算（EPS=0/欠損時は None）
    - すべて DuckDB の SQL と Python で完結。発注等の外部副作用はなし
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 将来リターン計算（複数ホライズン対応、入力検証あり）
    - calc_ic: スピアマンランク相関（Information Coefficient）計算（NULL/データ不足時は None）
    - rank: 同順位の平均ランク付けを行うユーティリティ
    - factor_summary: 各ファクター列の基本統計量（count, mean, std, min, max, median）を算出
    - 標準ライブラリのみで実装（pandas 等に依存しない）

- パブリック API 整理
  - 各サブパッケージの __init__.py で主要関数／ユーティリティをエクスポート（例: kabusys.ai.score_news, kabusys.research.calc_momentum 等）

### 変更
- （初回リリースのため過去変更はありません）

### 修正
- （初回リリースのため過去修正はありません）

### 既知の制限 / 注意事項
- OpenAI API に依存する処理（news_nlp, regime_detector）は API キーが必要。api_key 引数 or 環境変数 OPENAI_API_KEY を使用。未設定時は ValueError が発生する
- DuckDB テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）のスキーマおよび前提データが必要
- news_nlp と regime_detector は LLM レスポンスの堅牢性向上を図っているが、LLM の予期しない応答に対しては該当チャンク／記事をスキップする設計
- ETL/カレンダー周りは jquants_client の実装（fetch/save）に依存するため、そのクライアント実装が必要

### セキュリティ
- 特に報告するセキュリティ脆弱性は無し

---

今後の予定（例）
- モニタリング関連（監視・プロセス管理・アラート）機能の追加拡張
- テストと CI の充実、型注釈のより厳密なチェック
- パフォーマンス最適化（大規模データ処理時の DuckDB クエリチューニング）

（初回リリースのため過去のバージョン履歴はありません）