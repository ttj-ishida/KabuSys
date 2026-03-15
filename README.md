# KabuSys

KabuSys は日本株の自動売買システム向けに設計された Python パッケージの骨組み（スキャフォールド）です。モジュール構成を分離しているため、データ取得、売買ロジック（ストラテジー）、注文実行、監視の各機能を独立して実装・テストできます。

現在のバージョン: 0.1.0

---

## 機能一覧（想定）

このリポジトリは基本的なパッケージ構成のみを提供します。以下は各サブパッケージに期待される機能例です：

- data
  - 市場データの取得（ティック・板・OHLC 等）
  - 歴史データ（CSV / DB からのロード）
  - データ前処理（リサンプリング、欠損処理）
- strategy
  - 売買ロジックの実装（シグナル生成）
  - パラメータ管理・バックテスト用インターフェース
- execution
  - 注文送信（API 実装、発注・取消・約定管理）
  - 発注ルール（成行・指値・注文サイズ管理）
- monitoring
  - ログ・メトリクス収集
  - ダッシュボードやアラートの統合

※ 現状のコードベースでは各サブパッケージは空のプレースホルダになっています。ここを拡張して実装してください。

---

## セットアップ手順

推奨環境: Python 3.8 以上

1. リポジトリをクローン
   ```
   git clone <このリポジトリのURL>
   cd <リポジトリ名>
   ```

2. 仮想環境の作成（任意だが推奨）
   - macOS / Linux
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell)
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 開発インストール
   ```
   pip install -e .
   ```
   - 依存パッケージがあれば `requirements.txt` を追加して `pip install -r requirements.txt` を実行してください。

4. （任意）ビルドやパッケージ作成
   ```
   pip install build
   python -m build
   ```

---

## 使い方（簡単な例）

インストール後、パッケージのバージョンやサブパッケージをインポートできます。

```python
import kabusys

print(kabusys.__version__)   # 0.1.0

# サブパッケージ（現状はプレースホルダ）
import kabusys.data
import kabusys.strategy
import kabusys.execution
import kabusys.monitoring
```

開発者が実装する際の基本的なフローの例（擬似コード）:

- データ取得
  - kabusys.data で価格・板情報を取得
- シグナル生成
  - kabusys.strategy にて売買シグナルを生成
- 注文実行
  - kabusys.execution を通じて証券会社 API へ注文送信
- 監視
  - kabusys.monitoring でログやアラートを集約

各サブパッケージにクラスやインターフェースを定義して、依存を最小化する設計を推奨します（例えば StrategyInterface、ExecutionClientInterface など）。

---

## ディレクトリ構成

リポジトリ内の主要ファイル・ディレクトリ構成（現状）

- src/
  - kabusys/
    - __init__.py
    - data/
      - __init__.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

ファイル一覧（抜粋）:
- src/kabusys/__init__.py
  - パッケージメタ情報（__version__、__all__）
- src/kabusys/data/__init__.py
  - データ取得・管理用モジュール（実装場所）
- src/kabusys/strategy/__init__.py
  - ストラテジー実装用モジュール（実装場所）
- src/kabusys/execution/__init__.py
  - 注文実行・API ラッパー（実装場所）
- src/kabusys/monitoring/__init__.py
  - 監視・ロギング（実装場所）

---

## 拡張ガイド（実装のヒント）

- 各サブパッケージにインターフェースを用意する
  - 例: data.Provider, strategy.Strategy, execution.Client, monitoring.Backend
- テストを充実させる
  - 単体テスト（pytest など）で各コンポーネントを分離して検証
- シークレット（APIキー等）は環境変数や Vault で管理
- 本番運用では以下を考慮
  - 再接続・リトライロジック
  - 注文の冪等性・二重発注防止
  - フェイルセーフ（全ポジション強制クローズの仕組み）

---

## 貢献

バグ報告や機能追加の提案、プルリクエストは歓迎します。README の充実、テスト追加、ドキュメント整備などでも貢献できます。

提案フロー:
1. Issue を立てる（目的・変更点を明記）
2. フォーク -> ブランチ作成 -> 変更 -> テスト -> PR

---

## ライセンス

デフォルトでは明記していません。公開する場合は適切な OSS ライセンス（MIT、Apache-2.0 等）を選んで LICENSE ファイルを追加してください。

---

この README は現状の最小構成パッケージをもとにしたガイドラインです。各サブパッケージに具体的な実装を追加してプロジェクトを完成させてください。