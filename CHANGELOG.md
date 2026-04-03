# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースから推測して作成した初期リリースの変更履歴です。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-03
初期リリース。以下の主要機能・公開 API を追加しました。

### 追加 (Added)
- パッケージ骨組み
  - kabusys パッケージ初期化（__version__ = 0.1.0）。
  - 公開サブパッケージ: data, research, ai, monitoring, strategy, execution（__all__ に一部記載）。

- 設定管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能（プロジェクトルートを .git / pyproject.toml から探索）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込み無効化可能。
  - .env パーサ実装:
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱い（クォート有無での挙動差）。
  - 環境変数保護（既存 OS 環境変数を protected set として上書き防止）。
  - Settings クラスによる型付きプロパティ提供（J-Quants / kabu API / LINE / DB パス / 監視しきい値 / ログレベル等）。
  - 設定バリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）とユーティリティプロパティ（is_live / is_paper / is_dev）。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）を使って銘柄ごとのセンチメントを算出。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）。
    - バッチ処理（1 API 呼び出しあたり最大 20 銘柄）。
    - 1 銘柄あたり最大記事数・文字数トリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - JSON Mode を利用したレスポンス処理と厳密なバリデーション（results の存在確認、code の正規化、数値チェック）。
    - 429/ネットワーク断/タイムアウト/5xx のリトライ（指数バックオフ）。
    - スコアは ±1.0 にクリップ。
    - 成功した銘柄のみ ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT; 部分失敗時に既存データ保護）。
    - 公開関数: score_news(conn, target_date, api_key=None)
    - テスト容易性: _call_openai_api をパッチ差し替え可能。
  - レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードによる raw_news のフィルタリング、OpenAI によるマクロセンチメント評価（JSON 出力期待）。
    - リトライ・バックオフ、API 失敗時のフォールバック（macro_sentiment=0.0）。
    - 計算結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - 公開関数: score_regime(conn, target_date, api_key=None)

- データプラットフォーム（src/kabusys/data）
  - JPX カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar を用いた営業日判定 API: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - DB に値がない場合は曜日ベースのフォールバック（週末を休日扱い）。
    - next/prev の最大探索日数制限 (_MAX_SEARCH_DAYS) による無限ループ防止。
    - 夜間バッチ更新 job: calendar_update_job(conn, lookahead_days=...)（J-Quants から差分取得、バックフィル、健全性チェック、冪等保存）。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを公開（取得件数・保存件数・品質問題・エラー等を保持）。
    - 差分取得、バックフィル、品質チェック（quality モジュール）を想定した設計。
    - ETLResult.to_dict() による品質問題の辞書化（監査ログ向け）。
    - jquants_client 経由での取得/保存を前提。

- リサーチ / ファクター計算（src/kabusys/research）
  - factor_research.py
    - モメンタム: mom_1m/mom_3m/mom_6m、ma200_dev（200 日 MA 乖離）を計算（calc_momentum）。
    - ボラティリティ / 流動性: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算（calc_volatility）。
    - バリュー: latest raw_financials を用いた PER / ROE の計算（calc_value）。
    - DuckDB 上で SQL とウィンドウ関数を使った計算。データ不足時は None を返す設計。
  - feature_exploration.py
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=[1,5,21])（LEAD を利用、ホライズン検証）。
    - IC（Information Coefficient）計算: calc_ic(factor_records, forward_records, factor_col, return_col)（スピアマンのランク相関）。
    - ランク関数 rank(values)（同順位は平均ランク、丸めで ties を扱う）。
    - 統計サマリー: factor_summary(records, columns)（count/mean/std/min/max/median）。
  - research パッケージの公開関数を __init__ で整理（calc_momentum 等を再エクスポート）。

- ユーティリティ・設計上の注意点（クロスモジュール）
  - DuckDB 前提の実装（DuckDBPyConnection 入力）。
  - ルックアヘッドバイアス回避: 内部で datetime.today() / date.today() を参照しない関数設計（target_date に基づく処理）。
  - API 失敗時のフェイルセーフ: 例外を投げずにフォールバック（多くは 0.0 やスキップ）して処理を継続。
  - DB 書き込みは冪等性を重視（DELETE→INSERT や executemany を使った置換）。
  - テスト容易性を考慮した点: OpenAI 呼び出し点をモック可能にしている（関数分離）。

### 変更 (Changed)
- 初版のため過去バージョンからの変更はなし（0.1.0 が初期実装）。

### 修正 (Fixed)
- 初版のため過去バージョンからの修正はなし。

### セキュリティ (Security)
- 外部 API（OpenAI / J-Quants）キーは引数で注入可能か環境変数で読み込む設計。未設定時は ValueError を送出して明示的にエラーにする箇所あり（API キー漏洩リスク低減のためキーを直接ログ出力しない方針）。

---

注記:
- 本 CHANGELOG はソースコードの内容から推測して作成したものです。実際のリリースノートは開発者の意図やリリース日・追加変更に合わせて更新してください。