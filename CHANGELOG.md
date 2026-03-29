# Changelog

すべての重要な変更をここに記録します。本プロジェクトは Keep a Changelog の形式に従います。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]
- （現在のコードベースでは未リリースの変更はありません）

## [0.1.0] - 2026-03-29
初回リリース。日本株向け自動売買／データ基盤／リサーチ／AI 支援モジュール群を含む最初の実装。

### 追加
- パッケージ基礎
  - パッケージルートの定義（kabusys）とバージョン設定を追加（__version__ = 0.1.0）。
  - 主要サブパッケージを公開: data, research, ai, monitoring, strategy, execution（__all__ に一部を含む）。

- 環境設定（kabusys.config）
  - .env / .env.local ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルートの検出は __file__ を基点に `.git` または `pyproject.toml` を探索するため、CWD に依存しない挙動。
  - .env パーサーは以下の挙動をサポート/考慮:
    - コメント行、空行、`export KEY=val` フォーマット対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理。
    - クォートなし値のインラインコメント処理（直前が空白／タブの場合）。
  - 自動ロードの制御: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - OS 環境変数を保護するための protected keys 対応（`.env.local` は既存環境を上書き可能だが protected は除外）。
  - Settings クラスを提供し、主要設定をプロパティで取得可能:
    - J-Quants、kabu ステーション、Slack、DB パス（duckdb / sqlite）等のキー取得。
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）。
    - is_live / is_paper / is_dev の簡易判定プロパティ。

- データ（kabusys.data）
  - ETL パイプライン基盤（kabusys.data.pipeline）を実装:
    - 差分取得・バックフィルロジック、品質チェック統合のための ETLResult データクラスを公開。
    - DuckDB 上で最大日付取得などのユーティリティ実装。
  - カレンダー管理（kabusys.data.calendar_management）を実装:
    - market_calendar テーブルを基にした営業日判定・次営業日/前営業日取得・期間内営業日取得・SQ 判定など。
    - DB 未登録日は曜日ベースでフォールバック（週末を非営業日扱い）。
    - 夜間バッチ job (calendar_update_job) による J-Quants からの差分取得 + 冪等保存（バックフィル、健全性チェックあり）。
    - market_calendar がまばらにしかない場合でも next/prev/get_trading_days で一貫した結果を返す実装。
  - jquants_client との連携想定（fetch/save を呼ぶ設計）。

- リサーチ（kabusys.research）
  - ファクター計算モジュール（factor_research）:
    - モメンタム: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）。
    - ボラティリティ/流動性: 20日 ATR（atr_20 / atr_pct）、20日平均売買代金、出来高比率。
    - バリュー: PER（EPS が 0 または欠損なら None）、ROE（raw_financials から取得）。
    - DuckDB を用いた SQLベース実装。必要行不足時は None を返す設計。
  - 特徴量探索（feature_exploration）:
    - 将来リターン計算（calc_forward_returns）：任意ホライズン（デフォルト [1,5,21]）で LEAD を用いて計算。
    - IC（calc_ic）：Spearman ランク相関（ランクは同順位は平均ランク）を実装。データ不足(3未満)は None。
    - 統計サマリー（factor_summary）：count/mean/std/min/max/median を計算。
    - rank ユーティリティ（精度を考慮して round(v,12) で ties を扱う）。
  - zscore_normalize を data.stats から再利用できるようにエクスポート。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）:
    - raw_news と news_symbols を用い、銘柄ごとに記事を集約して OpenAI（gpt-4o-mini、JSON mode）でセンチメントを評価。
    - タイムウィンドウ定義（前日15:00 JST ～ 当日08:30 JST を UTC に変換して比較）。
    - 1チャンクで最大20銘柄、1銘柄あたり最大10記事・3000文字にトリムしてプロンプトを構成。
    - レスポンスは JSON の "results": [{"code": "XXXX", "score": 0.0}, ...] を期待し、バリデーションして ±1.0 にクリップ。
    - 再試行ロジック: 429・ネットワーク断・タイムアウト・5xx を指数バックオフでリトライ（最大回数制御）。
    - JSON パース耐性: 余分な前後テキストが混ざる場合に最外の {} を抽出するフォールバック。
    - 部分成功を許容するため、DB 書込みは対象コードのみ DELETE → INSERT（トランザクションで冪等に）。
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError。
  - 市場レジーム判定（kabusys.ai.regime_detector）:
    - ETF 1321（日経225連動型）の 200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出は news_nlp の calc_news_window を利用。
    - OpenAI 呼び出しは独立実装。API 失敗時は macro_sentiment=0.0 でフォールバックするフェイルセーフ。
    - レスポンスは JSON の {"macro_sentiment": 0.0} を期待。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT で冪等性を確保。失敗時は ROLLBACK（失敗ログを記録）して例外を再送出。
    - リトライ/バックオフ、5xx 判定などを考慮した堅牢な実装。

- 共通実装上の設計方針（目立つ点）
  - ルックアヘッドバイアス回避: 各種処理で datetime.today()/date.today() へ直接依存しない設計（target_date を明示的に渡す）。
  - DuckDB を前提に SQL と小さな Python 補助で処理（外部 DB・API への不要なアクセスを行わない）。
  - API 呼び出しはオプションで注入可能・テストしやすい作り（_call_openai_api の差し替えを想定）。
  - トランザクション（BEGIN/COMMIT/ROLLBACK）を用いた冪等保存と、部分失敗時に既存データを保護する戦略。
  - ロギングを随所に追加し、ワーニングや例外時の状況把握を容易に。

### 改善／内部
- OpenAI SDK（chat.completions.create）の利用に合わせた response_format={"type": "json_object"} の利用を想定した実装。
- API エラー処理は SDK の APIError の status_code を安全に扱う（getattr を利用）。
- DuckDB 0.10 の制約（executemany に空リスト不可）を回避するガードを追加。

### 既知の注意点（ドキュメント的な警告）
- OpenAI API キー（OPENAI_API_KEY）や J-Quants/Slack 等の必須環境変数が無い場合、該当機能は ValueError を投げる設計（呼び出し側での設定が必要）。
- .env 自動ロードはプロジェクトルートが特定できない場合はスキップされる（配布後の実行に配慮）。
- 一部機能は外部クライアント（jquants_client、kabu API クライアント等）実装を前提としているため、動作にはそれらの準備が必要。

---

この CHANGELOG は現行のソースコードから推測して作成しています。追加のリリースや修正があれば、上記に続けて追記してください。